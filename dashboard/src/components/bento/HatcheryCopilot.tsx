import React, { useState } from 'react';
import { Sparkles, FileText, ArrowUpRight, Mic, Send, Bot } from 'lucide-react';

interface ChatMessage {
  sender: 'user' | 'assistant';
  text: string;
}

export const HatcheryCopilot: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'user',
      text: 'What areas should I prioritize for managing my incubation batches today?'
    },
    {
      sender: 'assistant',
      text: '⚡ Hatchery Focus: Prioritize Day-10 candling for Batch KAY-01. Culling 48 unfertilized Penoy eggs now recovers ₱672 in local market value and saves 45.4 kWh in incubator electricity.'
    }
  ]);
  const [inputValue, setInputValue] = useState('');

  const quickPrompts = [
    'Day 10 Penoy Alert',
    'Calculate Yield',
    'Hatcher Schedule',
    'Breed Benchmark'
  ];

  const handleSend = (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim()) return;

    const newMsgs: ChatMessage[] = [...messages, { sender: 'user', text }];
    setMessages(newMsgs);
    setInputValue('');

    // Dynamic smart responses based on keywords
    setTimeout(() => {
      let reply = "I analyzed current hatchery telemetry. All 3 active batches are within normal temperature (37.5°C) and humidity (65% RH) parameters.";
      
      const lower = text.toLowerCase();
      if (lower.includes('penoy') || lower.includes('day 10')) {
        reply = "🥚 Day-10 Candling Update: 168 total Penoy eggs culled across active batches. Estimated commercial food salvage value is ₱2,352.00 @ ₱14.00/egg.";
      } else if (lower.includes('yield') || lower.includes('revenue') || lower.includes('calc')) {
        reply = "💰 Economic Yield Projection: Net financial benefit is ₱18,540.00 (+12.4% over last cycle), including ₱567.50 in avoided incubator power tariffs.";
      } else if (lower.includes('hatcher') || lower.includes('schedule') || lower.includes('transfer')) {
        reply = "📅 Hatcher Transfer Alert: Batch BATCH-2026-08-ITM-01 reaches Day 18 in 2 days. Prepare Hatcher Unit B2 at 75% RH and stop egg turning.";
      } else if (lower.includes('breed')) {
        reply = "📊 Breed Viability: Kayumanggi leads at 91.2% fertility, followed by Native Itim at 87.5% and Khaki Campbell at 84.8%.";
      }

      setMessages([...newMsgs, { sender: 'assistant', text: reply }]);
    }, 450);
  };

  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Hatchery AI Copilot
            </h3>
          </div>

          <div className="flex items-center gap-1.5 text-slate-500">
            <button className="p-1 rounded hover:text-slate-300 cursor-pointer" title="Export Chat Summary">
              <FileText className="w-3.5 h-3.5" />
            </button>
            <button className="p-1 rounded hover:text-slate-300 cursor-pointer" title="Open Full Screen">
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Chat Message Scrollable Container */}
        <div className="mt-3.5 space-y-2.5 max-h-48 overflow-y-auto pr-1">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[88%] p-2.5 rounded-2xl text-xs leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-[#1E2536] text-slate-200 rounded-tr-xs border border-[#2B354D]'
                    : 'bg-gradient-to-b from-[#161D2B] to-[#121723] text-slate-200 rounded-tl-xs border border-teal-500/30 shadow-md'
                }`}
              >
                {m.sender === 'assistant' && (
                  <span className="text-[10px] text-teal-400 font-bold block mb-1 flex items-center gap-1">
                    <Bot className="w-3 h-3 text-cyan-400" />
                    OvaLens Copilot
                  </span>
                )}
                <p>{m.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Prompt Pills + Input Bar */}
      <div className="mt-3 pt-3 border-t border-[#1F2636] space-y-2.5">
        {/* Prompt Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 text-[11px]">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleSend(prompt)}
              className="px-2.5 py-1 rounded-full bg-[#161B27] hover:bg-[#1E2536] text-slate-300 border border-[#222A3B] transition-all cursor-pointer whitespace-nowrap"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar with mic & send button */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Ask or search hatchery insights..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              className="w-full h-9 pl-3 pr-8 text-xs bg-[#161B27] border border-[#222A3B] rounded-full text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 transition-colors"
            />
            <button
              onClick={() => handleSend('Show Day 10 candling status')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              <Mic className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={() => handleSend()}
            className="w-9 h-9 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-slate-950 flex items-center justify-center shadow-md shadow-emerald-500/20 transition-all cursor-pointer flex-shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
