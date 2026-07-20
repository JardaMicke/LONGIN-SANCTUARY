"""
Roleplay Engine — manages multi-character roleplay scenarios.
Determines turn-taking, handles scenario contexts, and triggers auto-generation
of scene images or videos based on the roleplay narrative.
"""

from typing import AsyncGenerator, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from core.scenarios.scenario_manager import ScenarioManager
from core.characters.character_manager import CharacterManager
from core.inference.llm_engine import LLMEngine
from core.memory.stm_manager import STMManager
from core.generation.orchestrator import GenerationOrchestrator
from models.generation import TextToImageRequest


class RoleplayEngine:
    """Orchestrates turn-taking, narrative generation, and visual triggers in scenarios."""

    async def get_next_speakers(
        self,
        scenario,
        session_id: str,
        user_message: str,
        db: AsyncSession
    ) -> list[UUID]:
        """
        Determine which characters should speak next.
        Rules:
        - If the user explicitly @mentions a character, prioritize them.
        - Otherwise, let all characters respond sequentially (for full immersion),
          or determine priority based on context.
        """
        config = scenario.config or {}
        char_ids = [UUID(cid) for cid in config.get("characters", [])]

        if not char_ids:
            return []

        # Simple check for @mentions
        char_manager = CharacterManager(db)
        mentioned = []
        for cid in char_ids:
            char = await char_manager.get(cid)
            if char and f"@{char.name.lower()}" in user_message.lower():
                mentioned.append(cid)

        if mentioned:
            return mentioned

        # Default: all characters in the scenario speak in turn
        return char_ids

    async def run_roleplay_step(
        self,
        scenario_id: UUID,
        session_id: str,
        user_message: str,
        db: AsyncSession,
    ) -> AsyncGenerator[dict, None]:
        """
        Process a single step in a scenario roleplay:
        1. Fetch scenario and speakers.
        2. Stream response for each speaker.
        3. If configured, trigger background scene image generation.
        """
        scenario_manager = ScenarioManager(db)
        scenario = await scenario_manager.get(scenario_id)
        if not scenario:
            yield {"type": "error", "content": "Scenario not found"}
            return

        # 1. Save user message to STM (using scenario_id as prefix for keys)
        stm = STMManager()
        # Create a combined key or prefix for scenario sessions
        scenario_session_id = f"scenario:{scenario_id}:{session_id}"
        await stm.add_message(scenario_id, scenario_session_id, "user", user_message)

        # 2. Get characters who should respond
        speaker_ids = await self.get_next_speakers(scenario, scenario_session_id, user_message, db)
        char_manager = CharacterManager(db)
        llm_engine = LLMEngine()

        for char_id in speaker_ids:
            character = await char_manager.get(char_id)
            if not character:
                continue

            yield {"type": "speaker_start", "character": character.name, "character_id": str(char_id)}

            # Construct custom system prompt injecting scenario details
            config = scenario.config or {}
            rules = config.get("rules", "")
            scenario_context = (
                f"Active Scenario: {scenario.title}\n"
                f"Setting and narrative details:\n{scenario.description}\n"
            )
            if rules:
                scenario_context += f"Rules of this scenario:\n{rules}\n"

            # Prepend scenario context to character override prompt
            original_override = character.system_prompt_override or ""
            character.system_prompt_override = f"{scenario_context}\n{original_override}"

            # Stream character response
            full_response = ""
            async for chunk in llm_engine.stream_response(
                character_id=char_id,
                user_message=user_message,
                session_id=scenario_session_id,
                db=db,
            ):
                full_response += chunk
                yield {"type": "token", "content": chunk}

            # Save full response to STM under the scenario session
            await stm.add_message(char_id, scenario_session_id, "assistant", full_response)
            yield {"type": "speaker_done", "character": character.name, "content": full_response}

            # 3. Trigger auto-generation of scene visualization if configured
            if config.get("auto_generate_images", False):
                logger.info(f"Triggering auto scene image generation for scenario {scenario.title}")
                
                # Create description prompt combining narrative context
                image_prompt = (
                    f"A detailed cinematic scene representation from the narrative: {full_response[:200]}. "
                    f"Featuring character {character.name}. High quality, realistic anatomy, consistent visual style."
                )

                # Queue background generation
                try:
                    orchestrator = GenerationOrchestrator()
                    job = await orchestrator.create_job(
                        job_type="text_to_image",
                        params={
                            "prompt": image_prompt,
                            "character_id": str(char_id),
                            "scenario_id": str(scenario_id),
                        }
                    )
                    # Trigger in the background
                    import asyncio
                    asyncio.create_task(
                        orchestrator.run_text_to_image(
                            job_id=job.id,
                            request=TextToImageRequest(
                                prompt=image_prompt,
                                character_id=char_id,
                                width=settings.DEFAULT_IMAGE_WIDTH,
                                height=settings.DEFAULT_IMAGE_HEIGHT,
                            ),
                            db=db
                        )
                    )
                    yield {"type": "visual_trigger", "job_id": str(job.id), "character": character.name}
                except Exception as e:
                    logger.error(f"Failed to trigger auto image generation: {e}")
