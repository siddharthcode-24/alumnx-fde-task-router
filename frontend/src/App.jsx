import React, { useState } from "react";
import {
  Send,
  UploadCloud,
  Play,
  RotateCcw,
  Sparkles,
  Bot,
  User,
  Table,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet
} from "lucide-react";

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

const generateSampleEmails = (count = 250) => {
  const senders = [
    { name: "Suresh Kulkarni", email: "s.kulkarni@meridiansteel.co.in" },
    { name: "Ankit Bose", email: "ankit@railyardlogistics.in" },
    { name: "Nandita Reddy", email: "nandita@saassummit.in" },
    { name: "BHEL Procurement", email: "tender@bhel.in" },
    { name: "Vantage Billing", email: "accounts@vantagecloud.com" },
    { name: "Growth Agency", email: "leads@growthagency.io" }
  ];

  const templates = [
    { subject: "RFP - Enterprise Document Management System", body: "RFP for 1,200 users across 4 plants. Indicative budget Rs. 25 lakhs. Due by 2026-08-30." },
    { subject: "Quick demo request", body: "Hi team, we are a 30-person logistics startup in Pune. Can we get a demo next week?" },
    { subject: "Sponsorship confirmation needed", body: "India SaaS Summit sponsorship. Gold tier is Rs. 4,00,000. Need confirmation by tomorrow EOD." },
    { subject: "Tender Notice - Analytics Software", body: "Bharat Heavy Electricals Limited invites bids for software licences. Estimated value: Rs. 6,50,000. Last date: 2026-08-20." },
    { subject: "Invoice INV-2026-0331 Overdue", body: "Attached invoice for Rs. 1,18,000 against PO-88214 is 12 days overdue. Kindly process payment." },
    { subject: "3x your organic leads with SEO", body: "Hi, I noticed your website is not ranking on page 1. We do PR and content marketing. 15 min call?" },
    { subject: "Out of Office: Suresh Kulkarni", body: "I am out of office until 20th August with limited connectivity. For urgent tasks contact support." }
  ];

  const samples = [];
  for (let i = 1; i <= count; i++) {
    const sender = senders[i % senders.length];
    const template = templates[i % templates.length];
    const threadNum = Math.floor((i - 1) / 3) + 1;
    samples.push({
      email_id: `em_${String(i).padStart(5, "0")}`,
      thread_id: `th_${String(threadNum).padStart(4, "0")}`,
      message_index: (i - 1) % 3,
      from_name: sender.name,
      from_email: sender.email,
      to: "sales@company.com",
      cc: [],
      subject: template.subject,
      body: template.body,
      received_at: "2026-08-15T09:30:00+05:30",
      attachments: i % 4 === 0 ? ["spec.pdf"] : [],
      is_reply: (i - 1) % 3 > 0
    });
  }
  return samples;
};

export default function App() {
  const [candidateId, setCandidateId] = useState("priya.sharma@gmail.com");
  const [rawJsonText, setRawJsonText] = useState("");
  const [parsedEmails, setParsedEmails] = useState([]);
  const [parseError, setParseError] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestSummary, setIngestSummary] = useState(null);

  const [chatMessages, setChatMessages] = useState([
    {
      sender: "system",
      text: "Hello! Paste or generate an email batch. Once loaded, you can ask grounded questions about categories, triage queues, or skipped spam."
    }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);

  const handleJsonChange = (text) => {
    setRawJsonText(text);
    setParseError("");
    setIngestSummary(null);
    if (!text.trim()) {
      setParsedEmails([]);
      return;
    }
    try {
      const data = JSON.parse(text);
      if (Array.isArray(data)) setParsedEmails(data);
      else if (data.emails && Array.isArray(data.emails)) setParsedEmails(data.emails);
      else {
        setParseError("JSON must be an array of emails or have an 'emails' array.");
        setParsedEmails([]);
      }
    } catch (err) {
      setParseError("Invalid JSON syntax.");
    }
  };

  const handleLoadSamples = () => {
    const samples = generateSampleEmails(250);
    const jsonStr = JSON.stringify(samples, null, 2);
    setRawJsonText(jsonStr);
    handleJsonChange(jsonStr);
  };

  const handleIngestBatch = async () => {
    if (parsedEmails.length === 0) return;
    setIsIngesting(true);
    setIngestSummary(null);

    try {
      const batch = parsedEmails.slice(0, 100);
      const res = await fetch(`${BACKEND_BASE_URL}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: candidateId.trim().toLowerCase(),
          emails: batch
        })
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      setIngestSummary(data);
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "system",
          text: `Processed ${data.processed} emails: ${data.tasks_created} created, ${data.tasks_updated} updated, ${data.skipped} skipped.`
        }
      ]);
    } catch (err) {
      alert(`Ingestion error: ${err.message}`);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSendMessage = async (queryText = null) => {
    const query = (queryText || chatInput).trim();
    if (!query || isChatLoading) return;

    setChatMessages((prev) => [...prev, { sender: "user", text: query }]);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: candidateId.trim().toLowerCase(),
          query: query
        })
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        { sender: "bot", text: data.answer, supportingData: data.supporting_data }
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { sender: "bot", text: `Chat error: ${err.message}`, supportingData: null }
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-6 py-3.5 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="bg-blue-600 text-white p-2 rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 tracking-tight">Sales Inbox → Task Router</h1>
            <p className="text-xs text-slate-500 font-medium">ALUMNX AI LABS — FDE Challenge</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-slate-600">candidate_id:</label>
          <input
            type="email"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            className="text-xs px-3 py-1.5 bg-slate-100 border border-slate-300 rounded font-mono text-slate-700 w-64 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </header>

      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
        <div className="lg:col-span-7 flex flex-col space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-blue-600" />
                1. Input Batch JSON
              </h2>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleLoadSamples}
                  className="text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded transition"
                >
                  Load 250 Sample Emails
                </button>
                <button
                  type="button"
                  onClick={() => handleJsonChange("")}
                  className="text-xs font-medium text-slate-400 hover:text-slate-600 px-2 py-1.5"
                >
                  Clear
                </button>
              </div>
            </div>

            <textarea
              rows={6}
              value={rawJsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              placeholder="Paste array of email objects matching inbox.json schema here..."
              className="w-full text-xs font-mono bg-slate-50 border border-slate-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed text-slate-800"
            />

            {parseError && (
              <p className="mt-2 text-xs text-rose-600 flex items-center gap-1 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                {parseError}
              </p>
            )}

            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium">
                {parsedEmails.length} emails loaded
              </span>
              <button
                type="button"
                onClick={handleIngestBatch}
                disabled={isIngesting || parsedEmails.length === 0}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition shadow-sm"
              >
                {isIngesting ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Ingest & Route Batch (max 100)
              </button>
            </div>

            {ingestSummary && (
              <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs flex items-center justify-between text-emerald-900">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold">Ingestion Complete</span>
                </div>
                <div className="space-x-3 font-mono text-[11px]">
                  <span>Created: <b>{ingestSummary.tasks_created}</b></span>
                  <span>Updated: <b>{ingestSummary.tasks_updated}</b></span>
                  <span>Skipped: <b>{ingestSummary.skipped}</b></span>
                </div>
              </div>
            )}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Table className="w-4 h-4 text-blue-600" />
                2. Raw Batch Verification Table
              </h2>
              <span className="text-[11px] text-slate-500 font-medium">Pre-route Sanity View</span>
            </div>

            <div className="flex-1 overflow-x-auto max-h-[420px] border border-slate-100 rounded-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-100 text-slate-700 font-semibold sticky top-0 border-b border-slate-200">
                  <tr>
                    <th className="p-2.5">from_name</th>
                    <th className="p-2.5">from_email</th>
                    <th className="p-2.5">subject</th>
                    <th className="p-2.5">received_at</th>
                    <th className="p-2.5">thread_id</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {parsedEmails.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-12 text-slate-400 font-medium">
                        No batch loaded. Click &quot;Load 250 Sample Emails&quot; above.
                      </td>
                    </tr>
                  ) : (
                    parsedEmails.slice(0, 50).map((email, idx) => (
                      <tr key={email.email_id || idx} className="hover:bg-slate-50">
                        <td className="p-2.5 font-medium whitespace-nowrap">{email.from_name || "—"}</td>
                        <td className="p-2.5 font-mono text-[11px] text-slate-500">{email.from_email}</td>
                        <td className="p-2.5 max-w-[180px] truncate" title={email.subject}>
                          {email.subject}
                        </td>
                        <td className="p-2.5 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                          {email.received_at ? email.received_at.replace("T", " ").slice(0, 16) : "—"}
                        </td>
                        <td className="p-2.5 font-mono text-[11px] text-slate-500">{email.thread_id}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <div className="lg:col-span-5 flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden h-[780px]">
          <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bot className="w-5 h-5 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-800">3. Ops Query Assistant</h2>
            </div>
            <span className="text-[11px] font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              Grounded on DB
            </span>
          </div>

          <div className="p-3 bg-slate-50 border-b border-slate-100 flex flex-wrap gap-1.5">
            {[
              "How many proposal vs marketing emails?",
              "Show me everything in triage and why.",
              "What's our total deal value of open RFPs?",
              "How many emails were about GST refunds?",
              "Send Aarti an email about the RFP."
            ].map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSendMessage(q)}
                className="text-[11px] bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-full hover:bg-slate-100 transition"
              >
                {q}
              </button>
            ))}
          </div>

          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.sender !== "user" && (
                  <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-none"
                      : "bg-slate-100 text-slate-800 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.supportingData && Object.keys(msg.supportingData).length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-200">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                        <FileSpreadsheet className="w-3 h-3" /> Grounded Supporting Data:
                      </div>
                      <pre className="text-[11px] bg-white p-2 rounded border border-slate-200 font-mono text-slate-700 overflow-x-auto">
                        {JSON.stringify(msg.supportingData, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
                {msg.sender === "user" && (
                  <div className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}
            {isChatLoading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-slate-100 rounded-lg p-3 rounded-bl-none flex items-center space-x-1.5">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3 bg-white border-t border-slate-200 flex gap-2"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask questions about this email batch..."
              className="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isChatLoading || !chatInput.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white p-2 rounded-lg transition"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
