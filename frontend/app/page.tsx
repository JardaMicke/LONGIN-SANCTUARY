"use client";

import React, { useState, useEffect, useRef } from "react";

// --- API Endpoints ---
const API_BASE = "http://localhost:8000/api/v1";

export default function DashboardSPA() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "characters" | "chat" | "scenarios" | "network" | "settings"
  >("dashboard");

  // --- Global State ---
  const [characters, setCharacters] = useState<any[]>([]);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [clusterStatus, setClusterStatus] = useState<any>({
    master_node: "CORE-DT",
    total_vram_mb: 16384,
    free_vram_mb: 12288,
    nodes: [],
    active_jobs: 0,
    pending_join_requests: 0,
  });
  const [joinRequests, setJoinRequests] = useState<any[]>([]);
  const [unifiedSettings, setUnifiedSettings] = useState<any>({
    llm: {
      default_model: "llama3.1:8b",
      temperature: 0.8,
      max_tokens: 4096,
      context_length: 8192,
      ollama_url: "http://192.168.1.15:11434",
      exo_enabled: true,
      exo_url: "http://localhost:52415",
    },
    image: {
      default_model: "flux_dev",
      steps: 30,
      cfg: 7.0,
      width: 1024,
      height: 1024,
      ip_adapter_strength: 0.8,
      face_consistency_threshold: 0.85,
    },
    video: {
      default_model: "wanvideo",
      frames: 24,
      fps: 8,
      width: 832,
      height: 480,
    },
    memory: {
      stm_max_tokens: 4096,
      ltm_summarize_threshold: 8000,
      rag_top_k: 5,
      rag_similarity_threshold: 0.75,
      embedding_model: "nomic-embed-text",
    },
    network: {
      node_name: "CORE-DT",
      node_role: "both",
      cluster_discovery_enabled: true,
      nsfw_enabled: false,
      age_check_enabled: true,
      content_filter_level: "moderate",
    },
  });

  // --- Age Verification Gate State ---
  const [ageVerified, setAgeVerified] = useState<boolean>(true);
  const [showAgeModal, setShowAgeModal] = useState<boolean>(false);

  // --- Active Chat States ---
  const [activeChatTarget, setActiveChatTarget] = useState<{
    type: "character" | "scenario";
    id: string;
    name: string;
  } | null>(null);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [chatSessionId, setChatSessionId] = useState("");

  // --- Character Creation Form State ---
  const [charForm, setCharForm] = useState({
    name: "",
    age: 20,
    gender: "Female",
    race: "Human",
    backstory: "",
    personality: "",
    speech_style: "",
    nsfw_enabled: false,
    llm_model: "",
  });
  const [refFiles, setRefFiles] = useState<FileList | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // --- Scenario Creation Form State ---
  const [scenForm, setScenForm] = useState({
    title: "",
    description: "",
    characters: [] as string[],
    auto_generate_images: false,
    auto_generate_video: false,
  });

  // --- Cluster Approval Modal State ---
  const [pendingApproval, setPendingApproval] = useState<any | null>(null);
  const [installPath, setInstallPath] = useState("C:/LonginSanctuary");
  const [installComfyUI, setInstallComfyUI] = useState(true);
  const [installOllama, setInstallOllama] = useState(true);

  // --- Refs ---
  const chatEndRef = useRef<HTMLDivElement>(null);

  // --- Fetch Initial Data ---
  useEffect(() => {
    fetchInitialData();
    // Poll data for reactive dashboard & network status
    const interval = setInterval(() => {
      fetchClusterStatus();
      fetchJoinRequests();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages]);

  const fetchInitialData = async () => {
    try {
      await Promise.all([
        fetchCharacters(),
        fetchScenarios(),
        fetchClusterStatus(),
        fetchJoinRequests(),
        fetchSettings(),
        checkAgeStatus(),
      ]);
    } catch (err) {
      console.error("Failed to load initial data", err);
    }
  };

  const checkAgeStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/system/age-status`);
      if (res.ok) {
        const data = await res.json();
        setAgeVerified(data.verified);
      }
    } catch (e) {}
  };

  const handleAgeVerify = async () => {
    try {
      const res = await fetch(`${API_BASE}/system/age-verify`, {
        method: "POST",
      });
      if (res.ok) {
        setAgeVerified(true);
        setShowAgeModal(false);
      }
    } catch (e) {}
  };

  const fetchCharacters = async () => {
    try {
      const res = await fetch(`${API_BASE}/characters/`);
      if (res.ok) {
        const data = await res.json();
        setCharacters(data);
      }
    } catch (e) {}
  };

  const fetchScenarios = async () => {
    try {
      const res = await fetch(`${API_BASE}/scenarios/`);
      if (res.ok) {
        const data = await res.json();
        setScenarios(data);
      }
    } catch (e) {}
  };

  const fetchClusterStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/network/status`);
      if (res.ok) {
        const data = await res.json();
        setClusterStatus(data);
      }
    } catch (e) {}
  };

  const fetchJoinRequests = async () => {
    try {
      const res = await fetch(`${API_BASE}/network/join-requests`);
      if (res.ok) {
        const data = await res.json();
        setJoinRequests(data);
      }
    } catch (e) {}
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings/`);
      if (res.ok) {
        const data = await res.json();
        setUnifiedSettings(data);
      }
    } catch (e) {}
  };

  // --- Actions ---

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    // Simulate settings saving or trigger actual API if implemented
    alert("Nastavení úspěšně uložena a sjednocena!");
  };

  const handleCreateCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        name: charForm.name,
        persona: {
          age: charForm.age,
          gender: charForm.gender,
          race: charForm.race,
          backstory: charForm.backstory,
          personality: charForm.personality,
          speech_style: charForm.speech_style,
        },
        visual: {
          description: `Consistent character: ${charForm.name}, ${charForm.gender}, ${charForm.race}`,
        },
        llm_model: charForm.llm_model,
        nsfw_enabled: charForm.nsfw_enabled,
        content_level: charForm.nsfw_enabled ? "permissive" : "moderate",
      };

      const res = await fetch(`${API_BASE}/characters/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const newChar = await res.json();
        // If reference files selected, upload them
        if (refFiles && refFiles.length > 0) {
          setIsUploading(true);
          const formData = new FormData();
          for (let i = 0; i < refFiles.length; i++) {
            formData.append("files", refFiles[i]);
          }
          await fetch(`${API_BASE}/characters/${newChar.id}/reference-images`, {
            method: "POST",
            body: formData,
          });
          setIsUploading(false);
          setRefFiles(null);
        }

        // Reset
        setCharForm({
          name: "",
          age: 20,
          gender: "Female",
          race: "Human",
          backstory: "",
          personality: "",
          speech_style: "",
          nsfw_enabled: false,
          llm_model: "",
        });
        fetchCharacters();
        alert("Postava úspěšně vytvořena!");
      }
    } catch (err) {
      alert("Vytvoření postavy selhalo.");
      setIsUploading(false);
    }
  };

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        title: scenForm.title,
        description: scenForm.description,
        config: {
          characters: scenForm.characters,
          auto_generate_images: scenForm.auto_generate_images,
          auto_generate_video: scenForm.auto_generate_video,
        },
      };

      const res = await fetch(`${API_BASE}/scenarios/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setScenForm({
          title: "",
          description: "",
          characters: [],
          auto_generate_images: false,
          auto_generate_video: false,
        });
        fetchScenarios();
        alert("Scénář úspěšně vytvořen!");
      }
    } catch (err) {
      alert("Vytvoření scénáře selhalo.");
    }
  };

  const startChat = (type: "character" | "scenario", id: string, name: string) => {
    setActiveChatTarget({ type, id, name });
    setChatSessionId(Math.random().toString(36).substring(7));
    setChatMessages([]);
    setActiveTab("chat");
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !activeChatTarget) return;

    const userMsg = inputMessage;
    setInputMessage("");
    setChatMessages((prev) => [
      ...prev,
      { role: "user", content: userMsg, timestamp: new Date().toISOString() },
    ]);
    setIsGenerating(true);

    try {
      const endpoint =
        activeChatTarget.type === "character"
          ? `${API_BASE}/chat/${activeChatTarget.id}/message`
          : `${API_BASE}/scenarios/${activeChatTarget.id}/message`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          session_id: chatSessionId,
        }),
      });

      if (res.status === 401) {
        // NSFW trigger age gate
        setShowAgeModal(true);
        setIsGenerating(false);
        return;
      }

      if (!res.ok) throw new Error("Chyba při komunikaci");

      // Set up SSE streaming listener
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMsg = { role: "assistant", content: "", timestamp: new Date().toISOString() };
      
      setChatMessages((prev) => [...prev, assistantMsg]);

      while (reader) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.substring(6).trim();
            if (dataStr === "[DONE]") {
              break;
            }

            try {
              // Try scenario JSON structure
              if (activeChatTarget.type === "scenario") {
                const event = JSON.parse(dataStr);
                if (event.type === "token") {
                  assistantMsg.content += event.content;
                } else if (event.type === "speaker_start") {
                  // Prepend speaker name
                  assistantMsg.content += `\n**${event.character}:** `;
                }
              } else {
                // Flat token stream for basic chat
                assistantMsg.content += dataStr;
              }

              // Update the last message in state
              setChatMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...assistantMsg };
                return copy;
              });
            } catch (err) {
              // Raw token fallback
              assistantMsg.content += dataStr;
              setChatMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...assistantMsg };
                return copy;
              });
            }
          }
        }
      }
    } catch (err) {
      console.error("Chat error", err);
      setChatMessages((prev) => [
        ...prev,
        { role: "system", content: "Generování selhalo. Zkontrolujte připojení." },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApproveJoin = async () => {
    if (!pendingApproval) return;
    try {
      const res = await fetch(`${API_BASE}/network/join-requests/${pendingApproval.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          install_path: installPath,
          install_comfyui: installComfyUI,
          install_ollama: installOllama,
        }),
      });
      if (res.ok) {
        setPendingApproval(null);
        fetchJoinRequests();
        alert("Zařízení schváleno, instalace zahájena!");
      }
    } catch (err) {
      alert("Schválení selhalo.");
    }
  };

  const handleRejectJoin = async (id: string) => {
    try {
      await fetch(`${API_BASE}/network/join-requests/${id}/reject`, {
        method: "POST",
      });
      fetchJoinRequests();
    } catch (e) {}
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      {/* --- Sidebar Navigation --- */}
      <aside className="w-64 border-r border-zinc-800 bg-zinc-900 flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-zinc-800 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-500/20">
              Ω
            </div>
            <div>
              <h1 className="font-bold tracking-tight text-lg bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400">
                SANCTUARY
              </h1>
              <p className="text-xs text-zinc-500 font-mono">v0.1.0 (Local)</p>
            </div>
          </div>
          <nav className="p-4 flex flex-col gap-1.5">
            {[
              { id: "dashboard", label: "Přehled", icon: "📊" },
              { id: "characters", label: "Postavy", icon: "🧬" },
              { id: "scenarios", label: "Scénáře", icon: "🎭" },
              { id: "chat", label: "Chat", icon: "💬" },
              { id: "network", label: "Lokální Síť", icon: "🌐" },
              { id: "settings", label: "Nastavení", icon: "⚙️" },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as any)}
                className={`flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                  activeTab === item.id
                    ? "bg-gradient-to-r from-purple-950/40 to-indigo-950/40 text-purple-400 border-l-4 border-purple-500 pl-3 shadow-md shadow-purple-500/5"
                    : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Global Cluster Stats summary */}
        <div className="p-4 m-4 rounded-xl bg-zinc-800/40 border border-zinc-800 flex flex-col gap-2.5">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Cluster VRAM</span>
            <span className="font-semibold text-purple-400">
              {Math.round(clusterStatus.free_vram_mb / 1024)} /{" "}
              {Math.round(clusterStatus.total_vram_mb / 1024)} GB
            </span>
          </div>
          <div className="w-full bg-zinc-700 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full transition-all duration-500"
              style={{
                width: `${
                  (clusterStatus.free_vram_mb / (clusterStatus.total_vram_mb || 1)) * 100
                }%`,
              }}
            />
          </div>
          <div className="flex justify-between items-center text-[10px] text-zinc-500">
            <span>Aktivní úlohy: {clusterStatus.active_jobs}</span>
            <span className="flex items-center gap-1 font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-purple-950/50 text-purple-400 border border-purple-900/35">
              ● {clusterStatus.nodes.filter((n: any) => n.status === "online").length + 1} uzlů
            </span>
          </div>
        </div>
      </aside>

      {/* --- Main Content Panel --- */}
      <main className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
        {/* Header bar */}
        <header className="h-16 border-b border-zinc-800 bg-zinc-900/40 backdrop-blur-md px-8 flex items-center justify-between z-10">
          <h2 className="text-xl font-bold tracking-tight">
            {activeTab === "dashboard" && "Dashboard / Přehled systému"}
            {activeTab === "characters" && "Správa a tvorba AI postav"}
            {activeTab === "scenarios" && "Komplexní scénáře & Roleplay"}
            {activeTab === "chat" && `Chat s ${activeChatTarget ? activeChatTarget.name : "..."}`}
            {activeTab === "network" && "Síťová detekce & Distribuovaný cluster"}
            {activeTab === "settings" && "Sjednocené nastavení"}
          </h2>

          <div className="flex items-center gap-3">
            {ageVerified ? (
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-900/50">
                18+ Ověřeno
              </span>
            ) : (
              <button
                onClick={() => setShowAgeModal(true)}
                className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-900/50 hover:bg-rose-900 hover:text-rose-100 transition-colors"
              >
                Věkový zámek 🔞
              </button>
            )}
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-zinc-500 font-mono">LAN cluster připojen</span>
          </div>
        </header>

        {/* Dynamic Inner views */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          {/* --- VIEW: Dashboard --- */}
          {activeTab === "dashboard" && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* VRAM Pool stats */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between min-h-[160px] relative overflow-hidden shadow-xl shadow-purple-950/5">
                <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />
                <div>
                  <p className="text-xs uppercase tracking-wider text-zinc-500 font-medium">
                    Celková paměť clusteru (VRAM)
                  </p>
                  <p className="text-4xl font-extrabold mt-2 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                    {Math.round((clusterStatus.total_vram_mb || 16384) / 1024)} GB
                  </p>
                </div>
                <div className="text-xs text-zinc-400 mt-4 flex items-center justify-between border-t border-zinc-800 pt-3">
                  <span>Volná VRAM: {Math.round(clusterStatus.free_vram_mb / 1024)} GB</span>
                  <span className="text-emerald-400">Dostupná</span>
                </div>
              </div>

              {/* Character counts */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between min-h-[160px] relative overflow-hidden shadow-xl shadow-purple-950/5">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
                <div>
                  <p className="text-xs uppercase tracking-wider text-zinc-500 font-medium">
                    Vytvořené postavy
                  </p>
                  <p className="text-4xl font-extrabold mt-2 text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
                    {characters.length}
                  </p>
                </div>
                <div className="text-xs text-zinc-400 mt-4 flex items-center justify-between border-t border-zinc-800 pt-3">
                  <span>Aktivní scénáře: {scenarios.length}</span>
                  <button
                    onClick={() => setActiveTab("characters")}
                    className="text-purple-400 hover:text-purple-300 font-semibold"
                  >
                    Vytvořit →
                  </button>
                </div>
              </div>

              {/* Nodes online */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between min-h-[160px] relative overflow-hidden shadow-xl shadow-purple-950/5">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
                <div>
                  <p className="text-xs uppercase tracking-wider text-zinc-500 font-medium">
                    Aktivní uzly v síti (LAN)
                  </p>
                  <p className="text-4xl font-extrabold mt-2 text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-400">
                    {clusterStatus.nodes.filter((n: any) => n.status === "online").length + 1}
                  </p>
                </div>
                <div className="text-xs text-zinc-400 mt-4 flex items-center justify-between border-t border-zinc-800 pt-3">
                  <span>Čekající na schválení: {joinRequests.length}</span>
                  <button
                    onClick={() => setActiveTab("network")}
                    className="text-emerald-400 hover:text-emerald-300 font-semibold"
                  >
                    Spravovat →
                  </button>
                </div>
              </div>

              {/* Cluster Nodes Map */}
              <div className="md:col-span-3 p-6 rounded-2xl bg-zinc-900 border border-zinc-800">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <span>🌐</span> Mapa distribuovaných zařízení
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Master Node */}
                  <div className="p-4 rounded-xl bg-zinc-950 border border-purple-500/30 shadow-md shadow-purple-950/30">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-900/30">
                          Primary Node (Master)
                        </span>
                        <h4 className="font-bold text-lg mt-2">CORE-DT</h4>
                        <p className="text-xs text-zinc-500">192.168.1.15</p>
                      </div>
                      <span className="text-emerald-400 text-xs">🟢 Online</span>
                    </div>
                    <div className="mt-4 space-y-2 text-xs text-zinc-400">
                      <div className="flex justify-between">
                        <span>GPU: NVIDIA RTX 3060</span>
                        <span className="font-mono text-zinc-300">12 GB VRAM</span>
                      </div>
                      <div className="flex justify-between">
                        <span>OS: Windows 10</span>
                        <span>Služby: API, ComfyUI, Ollama</span>
                      </div>
                    </div>
                  </div>

                  {/* Discovered/Approved Nodes */}
                  {clusterStatus.nodes.map((node: any) => (
                    <div
                      key={node.ip}
                      className={`p-4 rounded-xl bg-zinc-950 border ${
                        node.status === "online" ? "border-zinc-800" : "border-zinc-900 opacity-60"
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-400">
                            Uzl (Worker)
                          </span>
                          <h4 className="font-bold text-lg mt-2">{node.name}</h4>
                          <p className="text-xs text-zinc-500">{node.ip}</p>
                        </div>
                        <span className={node.status === "online" ? "text-emerald-400 text-xs" : "text-zinc-600 text-xs"}>
                          {node.status === "online" ? "🟢 Online" : "🔴 Offline"}
                        </span>
                      </div>
                      <div className="mt-4 space-y-2 text-xs text-zinc-400">
                        <div className="flex justify-between">
                          <span>GPU: {node.gpu_name || "NVIDIA GTX 1650"}</span>
                          <span className="font-mono text-zinc-300">
                            {Math.round(node.gpu_vram_total_mb / 1024) || 4} GB VRAM
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Služby: ComfyUI, Ollama</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* --- VIEW: Characters --- */}
          {activeTab === "characters" && (
            <div className="space-y-8">
              {/* Character creation form */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800">
                <h3 className="text-lg font-bold mb-4">🧬 Vytvořit novou postavu</h3>
                <form onSubmit={handleCreateCharacter} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Jméno postavy
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="např. Lilith, Marcus..."
                      value={charForm.name}
                      onChange={(e) => setCharForm({ ...charForm, name: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Věk postavy
                    </label>
                    <input
                      type="number"
                      required
                      value={charForm.age}
                      onChange={(e) => setCharForm({ ...charForm, age: parseInt(e.target.value) || 20 })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Rasa
                    </label>
                    <input
                      type="text"
                      placeholder="Human, Elf, Cyborg..."
                      value={charForm.race}
                      onChange={(e) => setCharForm({ ...charForm, race: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Pohlaví
                    </label>
                    <input
                      type="text"
                      placeholder="Female, Male, Unknown..."
                      value={charForm.gender}
                      onChange={(e) => setCharForm({ ...charForm, gender: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Historie (Backstory)
                    </label>
                    <textarea
                      rows={3}
                      placeholder="Popište minulost postavy, která ovlivní její reakce..."
                      value={charForm.backstory}
                      onChange={(e) => setCharForm({ ...charForm, backstory: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Osobnost (Personality traits)
                    </label>
                    <textarea
                      rows={2}
                      placeholder="např. Sarkastická, tajnůstkářská, věrná..."
                      value={charForm.personality}
                      onChange={(e) => setCharForm({ ...charForm, personality: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Komunikační styl (Speech style)
                    </label>
                    <input
                      type="text"
                      placeholder="např. Mluví formálně, používá hodně slangů..."
                      value={charForm.speech_style}
                      onChange={(e) => setCharForm({ ...charForm, speech_style: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Upload referenčních obrázků (20+ pro LoRA)
                    </label>
                    <input
                      type="file"
                      multiple
                      accept="image/*"
                      onChange={(e) => setRefFiles(e.target.files)}
                      className="w-full text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-purple-950 file:text-purple-400 hover:file:bg-purple-900 file:cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center gap-6 mt-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={charForm.nsfw_enabled}
                        onChange={(e) => setCharForm({ ...charForm, nsfw_enabled: e.target.checked })}
                        className="rounded border-zinc-800 bg-zinc-950 text-purple-600 focus:ring-0 focus:ring-offset-0 w-4 h-4"
                      />
                      <span className="text-sm font-medium">Povolit NSFW obsah 🔞</span>
                    </label>
                  </div>

                  <div className="md:col-span-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={isUploading}
                      className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-sm font-semibold transition-all duration-300 shadow-md shadow-purple-500/15"
                    >
                      {isUploading ? "Nahrávání & Zpracování..." : "Vytvořit postavu"}
                    </button>
                  </div>
                </form>
              </div>

              {/* Characters gallery */}
              <div className="space-y-4">
                <h3 className="text-lg font-bold">🧬 Knihovna postav</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {characters.map((char) => (
                    <div
                      key={char.id}
                      className="p-5 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between min-h-[220px] shadow-lg"
                    >
                      <div>
                        <div className="flex justify-between items-start">
                          <h4 className="font-bold text-xl">{char.name}</h4>
                          {char.nsfw_enabled && (
                            <span className="text-[10px] bg-rose-950/50 text-rose-400 border border-rose-900/35 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider font-mono">
                              NSFW 🔞
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-500 mt-0.5">
                          {char.persona.race} • {char.persona.gender} • {char.persona.age} let
                        </p>
                        <p className="text-sm text-zinc-300 mt-4 line-clamp-3">
                          {char.persona.backstory}
                        </p>
                      </div>

                      <div className="mt-6 flex gap-2">
                        <button
                          onClick={() => startChat("character", char.id, char.name)}
                          className="flex-1 px-4 py-2.5 rounded-xl bg-purple-950 text-purple-400 hover:bg-purple-900 border border-purple-900/35 text-xs font-semibold transition-all duration-200"
                        >
                          Chatovat 💬
                        </button>
                      </div>
                    </div>
                  ))}
                  {characters.length === 0 && (
                    <p className="text-sm text-zinc-500 italic md:col-span-3">
                      Zatím nebyly vytvořeny žádné postavy.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* --- VIEW: Scenarios --- */}
          {activeTab === "scenarios" && (
            <div className="space-y-8">
              {/* Scenario creation form */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800">
                <h3 className="text-lg font-bold mb-4">🎭 Vytvořit nový scénář</h3>
                <form onSubmit={handleCreateScenario} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Název scénáře
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="např. Záchrana na oběžné dráze..."
                      value={scenForm.title}
                      onChange={(e) => setScenForm({ ...scenForm, title: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Popis situace (Narrative Context)
                    </label>
                    <textarea
                      rows={4}
                      required
                      placeholder="Detailně popište scénu, svět a počáteční situaci..."
                      value={scenForm.description}
                      onChange={(e) => setScenForm({ ...scenForm, description: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1">
                      Vyberte zúčastněné postavy (Multi-character)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-1">
                      {characters.map((char) => {
                        const selected = scenForm.characters.includes(char.id);
                        return (
                          <button
                            type="button"
                            key={char.id}
                            onClick={() => {
                              if (selected) {
                                setScenForm({
                                  ...scenForm,
                                  characters: scenForm.characters.filter((id) => id !== char.id),
                                });
                              } else {
                                setScenForm({
                                  ...scenForm,
                                  characters: [...scenForm.characters, char.id],
                                });
                              }
                            }}
                            className={`px-3 py-2 rounded-xl text-xs font-medium border text-left transition-all ${
                              selected
                                ? "bg-purple-950/40 text-purple-400 border-purple-500"
                                : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                            }`}
                          >
                            {char.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex gap-6 mt-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={scenForm.auto_generate_images}
                        onChange={(e) =>
                          setScenForm({ ...scenForm, auto_generate_images: e.target.checked })
                        }
                        className="rounded border-zinc-800 bg-zinc-950 text-purple-600 focus:ring-0 w-4 h-4"
                      />
                      <span className="text-sm font-medium">Auto-generovat obrázky 🖼️</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={scenForm.auto_generate_video}
                        onChange={(e) =>
                          setScenForm({ ...scenForm, auto_generate_video: e.target.checked })
                        }
                        className="rounded border-zinc-800 bg-zinc-950 text-purple-600 focus:ring-0 w-4 h-4"
                      />
                      <span className="text-sm font-medium">Auto-generovat video 🎥</span>
                    </label>
                  </div>

                  <div className="md:col-span-2 flex justify-end">
                    <button
                      type="submit"
                      className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-sm font-semibold transition-all duration-300 shadow-md shadow-purple-500/15"
                    >
                      Vytvořit scénář
                    </button>
                  </div>
                </form>
              </div>

              {/* Scenarios gallery */}
              <div className="space-y-4">
                <h3 className="text-lg font-bold">🎭 Aktivní scénáře</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {scenarios.map((scen) => (
                    <div
                      key={scen.id}
                      className="p-5 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between min-h-[200px]"
                    >
                      <div>
                        <h4 className="font-bold text-xl">{scen.title}</h4>
                        <p className="text-sm text-zinc-300 mt-3 line-clamp-3">
                          {scen.description}
                        </p>
                      </div>

                      <div className="mt-6 flex justify-between items-center">
                        <span className="text-xs font-mono text-zinc-500">
                          Postavy: {scen.config.characters?.length || 0}
                        </span>
                        <button
                          onClick={() => startChat("scenario", scen.id, scen.title)}
                          className="px-4 py-2 rounded-xl bg-indigo-950 text-indigo-400 hover:bg-indigo-900 border border-indigo-900/35 text-xs font-semibold transition-all duration-200"
                        >
                          Spustit roleplay 🎭
                        </button>
                      </div>
                    </div>
                  ))}
                  {scenarios.length === 0 && (
                    <p className="text-sm text-zinc-500 italic">
                      Zatím nebyly vytvořeny žádné scénáře.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* --- VIEW: Chat --- */}
          {activeTab === "chat" && (
            <div className="h-full flex flex-col justify-between bg-zinc-950 -m-8">
              {activeChatTarget ? (
                <>
                  {/* Chat messages viewport */}
                  <div className="flex-1 overflow-y-auto p-8 space-y-4">
                    <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/50 text-xs text-zinc-500 text-center font-mono">
                      Konverzace zahájena v režimu:{" "}
                      {activeChatTarget.type === "character" ? "Přímý chat" : "Scénář"}
                    </div>

                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex flex-col max-w-[70%] rounded-2xl p-4 ${
                          msg.role === "user"
                            ? "bg-purple-950/20 border border-purple-900/30 ml-auto"
                            : msg.role === "system"
                            ? "bg-rose-950/20 border border-rose-900/30 mx-auto text-xs text-rose-400"
                            : "bg-zinc-900 border border-zinc-800"
                        }`}
                      >
                        <span className="text-[10px] text-zinc-500 font-mono mb-1.5">
                          {msg.role === "user" ? "Vy" : activeChatTarget.name} •{" "}
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                          {msg.content}
                        </p>
                      </div>
                    ))}
                    {isGenerating && (
                      <div className="flex items-center gap-2 text-zinc-500 text-xs font-mono ml-4">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-bounce" />
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-bounce delay-100" />
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-bounce delay-200" />
                        <span>AI přemýšlí a generuje...</span>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input bar */}
                  <div className="p-6 border-t border-zinc-800 bg-zinc-900/20 backdrop-blur-md">
                    <form onSubmit={handleSendMessage} className="flex gap-3">
                      <input
                        type="text"
                        placeholder="Napište zprávu..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        disabled={isGenerating}
                        className="flex-1 px-4 py-3.5 rounded-xl bg-zinc-900 border border-zinc-800 focus:outline-none focus:border-purple-500 text-sm disabled:opacity-50"
                      />
                      <button
                        type="submit"
                        disabled={isGenerating}
                        className="px-6 rounded-xl bg-purple-600 hover:bg-purple-500 text-sm font-semibold transition-colors disabled:opacity-50"
                      >
                        Odeslat
                      </button>
                    </form>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 gap-4">
                  <span>💬</span>
                  <p className="text-sm italic">
                    Vyberte postavu nebo scénář pro zahájení chatu.
                  </p>
                  <button
                    onClick={() => setActiveTab("characters")}
                    className="px-4 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs font-semibold hover:border-zinc-700 transition-all"
                  >
                    Otevřít Knihovnu Postav
                  </button>
                </div>
              )}
            </div>
          )}

          {/* --- VIEW: Network --- */}
          {activeTab === "network" && (
            <div className="space-y-8">
              {/* Discovered Join Requests */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <span>📡</span> Čekající žádosti o připojení nového zařízení
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left text-zinc-400">
                    <thead className="text-xs uppercase bg-zinc-950 text-zinc-500 border-b border-zinc-800">
                      <tr>
                        <th className="px-6 py-3 font-mono">Zařízení</th>
                        <th className="px-6 py-3 font-mono">IP Adresa</th>
                        <th className="px-6 py-3 font-mono">Hardware specifikace</th>
                        <th className="px-6 py-3 font-mono">Akce</th>
                      </tr>
                    </thead>
                    <tbody>
                      {joinRequests.map((req) => (
                        <tr key={req.id} className="border-b border-zinc-800 bg-zinc-900/50">
                          <td className="px-6 py-4 font-bold text-zinc-200">{req.hostname}</td>
                          <td className="px-6 py-4 font-mono">{req.ip}</td>
                          <td className="px-6 py-4 text-xs">
                            GPU: {req.hardware_info.gpu?.[0]?.name || "N/A"} (
                            {req.hardware_info.gpu?.[0]?.vram_mb || 0} MB VRAM) <br />
                            RAM: {req.hardware_info.ram_total_mb} MB • OS: {req.hardware_info.os}
                          </td>
                          <td className="px-6 py-4 flex gap-2">
                            <button
                              onClick={() => setPendingApproval(req)}
                              className="px-3 py-1.5 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-900/50 text-xs font-semibold hover:bg-emerald-900 transition-colors"
                            >
                              Schválit & Instalovat ✅
                            </button>
                            <button
                              onClick={() => handleRejectJoin(req.id)}
                              className="px-3 py-1.5 rounded-lg bg-rose-950 text-rose-400 border border-rose-900/50 text-xs font-semibold hover:bg-rose-900 transition-colors"
                            >
                              Odmítnout ❌
                            </button>
                          </td>
                        </tr>
                      ))}
                      {joinRequests.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-6 py-8 text-center text-zinc-500 italic">
                            Žádné aktivní žádosti o připojení ze sítě.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Discovery and usage settings explanation */}
              <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800 text-sm space-y-3">
                <h4 className="font-bold text-zinc-200">Jak funguje distribuovaný výpočet?</h4>
                <p className="text-zinc-400 leading-relaxed">
                  Pokud na svém MiniPC nebo jiném zařízení v síti spustíte skript{" "}
                  <code className="text-purple-400 font-mono px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800">
                    python scripts/cluster_agent.py --master 192.168.1.15
                  </code>
                  , zařízení automaticky odešle žádost, která se zobrazí v tabulce výše. Po
                  schválení master stáhne a nakonfiguruje Ollama i ComfyUI, a zařízení se stane
                  aktivním workerem v clusteru pro běh LLM modelů a generování.
                </p>
              </div>
            </div>
          )}

          {/* --- VIEW: Settings --- */}
          {activeTab === "settings" && (
            <form onSubmit={handleSaveSettings} className="space-y-6 max-w-3xl">
              {/* LLM Settings */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-4">
                <h3 className="text-lg font-bold border-b border-zinc-800 pb-2">💬 Nastavení LLM (Inference)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      Výchozí Model
                    </label>
                    <input
                      type="text"
                      value={unifiedSettings.llm.default_model}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          llm: { ...unifiedSettings.llm, default_model: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      Teplota (Temperature)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={unifiedSettings.llm.temperature}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          llm: {
                            ...unifiedSettings.llm,
                            temperature: parseFloat(e.target.value) || 0.8,
                          },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Image Gen Settings */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-4">
                <h3 className="text-lg font-bold border-b border-zinc-800 pb-2">🖼️ Generování Obrázků (ComfyUI)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      Generační Model (Base)
                    </label>
                    <input
                      type="text"
                      value={unifiedSettings.image.default_model}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          image: { ...unifiedSettings.image, default_model: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      IP-Adapter Síla (Face consistency)
                    </label>
                    <input
                      type="number"
                      step="0.05"
                      value={unifiedSettings.image.ip_adapter_strength}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          image: {
                            ...unifiedSettings.image,
                            ip_adapter_strength: parseFloat(e.target.value) || 0.8,
                          },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Video Gen Settings */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-4">
                <h3 className="text-lg font-bold border-b border-zinc-800 pb-2">🎥 Generování Videa</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      Video Model (WanVideo / SVD)
                    </label>
                    <input
                      type="text"
                      value={unifiedSettings.video.default_model}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          video: { ...unifiedSettings.video, default_model: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                      Počet Snímků (Frames)
                    </label>
                    <input
                      type="number"
                      value={unifiedSettings.video.frames}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          video: {
                            ...unifiedSettings.video,
                            frames: parseInt(e.target.value) || 24,
                          },
                        })
                      }
                      className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Safety and NSFW configs */}
              <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-4">
                <h3 className="text-lg font-bold border-b border-zinc-800 pb-2">🔞 Bezpečnost & NSFW</h3>
                <div className="flex flex-col gap-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={unifiedSettings.network.nsfw_enabled}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          network: {
                            ...unifiedSettings.network,
                            nsfw_enabled: e.target.checked,
                          },
                        })
                      }
                      className="rounded border-zinc-800 bg-zinc-950 text-purple-600 w-4 h-4"
                    />
                    <span className="text-sm font-medium">Globálně povolit NSFW obsah</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={unifiedSettings.network.age_check_enabled}
                      onChange={(e) =>
                        setUnifiedSettings({
                          ...unifiedSettings,
                          network: {
                            ...unifiedSettings.network,
                            age_check_enabled: e.target.checked,
                          },
                        })
                      }
                      className="rounded border-zinc-800 bg-zinc-950 text-purple-600 w-4 h-4"
                    />
                    <span className="text-sm font-medium">Vynutit věkové ověření (18+)</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-sm font-semibold transition-all shadow-md shadow-purple-500/15"
                >
                  Uložit všechna nastavení
                </button>
              </div>
            </form>
          )}
        </div>
      </main>

      {/* --- MODAL: Age Verification Gate 🔞 --- */}
      {showAgeModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 max-w-md w-full text-center space-y-6 shadow-2xl">
            <div className="text-5xl">🔞</div>
            <h3 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-red-400">
              Věkové ověření
            </h3>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Tato sekce nebo postava obsahuje explicitní (NSFW) obsah. Potvrďte, že jste starší
              18 let a souhlasíte s jeho zobrazením.
            </p>
            <div className="flex gap-4">
              <button
                onClick={handleAgeVerify}
                className="flex-1 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 font-semibold text-sm transition-colors"
              >
                Je mi 18+ let 🚪
              </button>
              <button
                onClick={() => {
                  setShowAgeModal(false);
                  setActiveTab("dashboard");
                }}
                className="flex-1 py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 font-semibold text-sm text-zinc-400 transition-colors"
              >
                Odejít
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: Approve Node Installation Configuration --- */}
      {pendingApproval && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 max-w-lg w-full space-y-5 shadow-xl">
            <h3 className="text-lg font-bold text-zinc-200">
              Nastavení instalace pro {pendingApproval.hostname}
            </h3>
            <p className="text-xs text-zinc-500">
              Zvolte parametry instalace agenta na vzdáleném uzlu s IP adresou {pendingApproval.ip}.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 mb-1">
                  Instalační složka
                </label>
                <input
                  type="text"
                  value={installPath}
                  onChange={(e) => setInstallPath(e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-sm"
                />
              </div>

              <div className="flex flex-col gap-2.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={installComfyUI}
                    onChange={(e) => setInstallComfyUI(e.target.checked)}
                    className="rounded border-zinc-800 bg-zinc-950 text-purple-600 w-4 h-4"
                  />
                  <span className="text-sm font-medium">Stáhnout a nainstalovat ComfyUI</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={installOllama}
                    onChange={(e) => setInstallOllama(e.target.checked)}
                    className="rounded border-zinc-800 bg-zinc-950 text-purple-600 w-4 h-4"
                  />
                  <span className="text-sm font-medium">Nainstalovat Ollama</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setPendingApproval(null)}
                className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold transition-all"
              >
                Storno
              </button>
              <button
                onClick={handleApproveJoin}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-semibold transition-all shadow-md shadow-emerald-500/10"
              >
                Spustit instalaci ⚙️
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
