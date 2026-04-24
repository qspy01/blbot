"use client";
import React, { useState } from 'react';
import { Download, Scissors, Loader2, AlertCircle, CheckCircle2, ShieldCheck, Video } from 'lucide-react';

export default function Page() {
  const [url, setUrl] = useState('');
  const [isTrimming, setIsTrimming] = useState(false);
  const [startTime, setStartTime] = useState<number | ''>('');
  const [endTime, setEndTime] = useState<number | ''>('');
  
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [resultUrl, setResultUrl] = useState('');

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Upewniamy się, że użytkownik cokolwiek wpisał
    if (!url || url.trim() === '') {
      setStatus('error');
      setMessage('Proszę podać poprawny link do materiału wideo.');
      return;
    }

    setStatus('loading');
    setResultUrl('');
    
    // Dynamicznie tworzymy adres do naszego serwera API (Port 8000)
    const apiUrl = typeof window !== 'undefined' 
      ? `${window.location.protocol}//${window.location.hostname}:8000` 
      : 'http://localhost:8000';

    setMessage(`Łączenie z serwerem: ${apiUrl}...`);

    try {
      const res = await fetch(`${apiUrl}/api/v1/downloads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          start_time: isTrimming && startTime !== '' ? Number(startTime) : null,
          end_time: isTrimming && endTime !== '' ? Number(endTime) : null
        })
      });

      if (!res.ok) {
        throw new Error(`Błąd serwera (Kod: ${res.status}). Sprawdź czy backend działa na porcie 8000.`);
      }

      const data = await res.json();
      setMessage('Zadanie przyjęte. Oczekiwanie na pobranie pliku...');
      
      // Zaczynamy odpytywać backend o status
      pollTaskStatus(data.task_id, apiUrl);

    } catch (err: any) {
      setStatus('error');
      setMessage(`Błąd połączenia: ${err.message || 'Nie można połączyć się z serwerem API na porcie 8000.'}`);
    }
  };

  const pollTaskStatus = async (taskId: string, apiUrl: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/downloads/status/${taskId}`);
      const data = await res.json();

      if (data.status === 'SUCCESS') {
        setStatus('success');
        // Jeśli backend zwrócił względną ścieżkę (/downloads/...), doklejamy adres serwera
        const finalUrl = data.url.startsWith('/') ? `${apiUrl}${data.url}` : data.url;
        setResultUrl(finalUrl);
        setMessage('Gotowe! Twój plik został pomyślnie przetworzony i jest gotowy do pobrania.');
      } 
      else if (data.status === 'FAILURE') {
        setStatus('error');
        setMessage(`Pobieranie nie powiodło się: ${data.error || 'Serwis odrzucił link.'}`);
      } 
      else {
        // PROCESSING LUB PENDING
        setMessage(data.status === 'PROCESSING' ? 'Serwer pobiera i przetwarza wideo (to może potrwać)...' : 'Zlecenie jest w kolejce...');
        setTimeout(() => pollTaskStatus(taskId, apiUrl), 2500);
      }
    } catch (err) {
      setStatus('error');
      setMessage('Przerwano połączenie z serwerem podczas odpytywania o status.');
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-indigo-500 selection:text-white flex flex-col">
      <div className="w-full bg-neutral-900 border-b border-neutral-800 py-3 text-center flex items-center justify-center">
        <span className="text-xs uppercase tracking-widest text-neutral-500 font-bold tracking-[0.2em]">Miejsce na Reklamę / Ogłoszenie</span>
      </div>

      <main className="flex-grow flex flex-col items-center justify-center px-4 py-12 md:py-20">
        <div className="text-center mb-10 w-full max-w-3xl">
          <div className="flex items-center justify-center mb-4 space-x-3">
            <Video className="text-indigo-500" size={48} />
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400">Ssij.</h1>
          </div>
          <p className="text-lg md:text-xl text-neutral-400 mt-4 leading-relaxed">Nowoczesny system pobierania multimediów.</p>
        </div>

        <div className="w-full max-w-2xl bg-neutral-900 border border-neutral-800 rounded-3xl shadow-2xl overflow-hidden p-6 sm:p-8">
          <form onSubmit={handleDownload} className="space-y-6">
            <div className="relative group">
              <input type="url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Wklej link (np. z YouTube, TikTok)..." disabled={status === 'loading'} className="w-full bg-neutral-950 border border-neutral-700 text-white rounded-2xl px-5 py-4 pl-5 pr-14 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all placeholder-neutral-600 disabled:opacity-50 text-lg shadow-inner" />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-500"><Download size={24} /></div>
            </div>

            <div className="bg-neutral-950 rounded-2xl p-5 border border-neutral-800/50">
              <label className="flex items-center space-x-3 cursor-pointer group w-fit">
                <div className="relative flex items-center justify-center">
                  <input type="checkbox" checked={isTrimming} onChange={(e) => setIsTrimming(e.target.checked)} disabled={status === 'loading'} className="peer sr-only" />
                  <div className="w-6 h-6 border-2 border-neutral-600 rounded bg-neutral-900 peer-checked:bg-indigo-500 peer-checked:border-indigo-500 transition-all flex items-center justify-center">
                     <CheckCircle2 size={16} className="text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                  </div>
                </div>
                <span className="text-neutral-300 font-medium flex items-center space-x-2 group-hover:text-white transition-colors">
                  <Scissors size={18} className="text-neutral-500 group-hover:text-indigo-400 transition-colors" />
                  <span>Chcę przyciąć materiał wideo (od - do)</span>
                </span>
              </label>

              {isTrimming && (
                <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="relative"><label className="block text-xs text-neutral-500 uppercase tracking-wider mb-2 font-semibold">Od (sekunda)</label><input type="number" min="0" value={startTime} onChange={(e) => setStartTime(e.target.value === '' ? '' : Number(e.target.value))} className="w-full bg-neutral-900 border border-neutral-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="0" /></div>
                  <div className="relative"><label className="block text-xs text-neutral-500 uppercase tracking-wider mb-2 font-semibold">Do (sekunda)</label><input type="number" min="1" value={endTime} onChange={(e) => setEndTime(e.target.value === '' ? '' : Number(e.target.value))} className="w-full bg-neutral-900 border border-neutral-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="30" /></div>
                </div>
              )}
            </div>

            <button type="submit" disabled={status === 'loading'} className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-bold py-4 px-8 rounded-2xl transition-all transform hover:scale-[1.01] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100 flex items-center justify-center space-x-3 shadow-[0_0_40px_-10px_rgba(99,102,241,0.5)] text-lg">
              {status === 'loading' ? <><Loader2 className="animate-spin" size={24} /><span>Przetwarzanie zlecenia...</span></> : <span>Rozpocznij Pobieranie</span>}
            </button>
          </form>

          {/* EKRAN STATUSU / BŁĘDÓW */}
          {status !== 'idle' && (
            <div className={`mt-8 p-5 rounded-2xl border ${status === 'loading' ? 'bg-indigo-950/20 border-indigo-500/30' : status === 'success' ? 'bg-emerald-950/20 border-emerald-500/30' : 'bg-red-950/20 border-red-500/30'}`}>
              <div className="flex flex-col items-center justify-center text-center space-y-4">
                {status === 'loading' && <Loader2 className="animate-spin text-indigo-400" size={36} />}
                {status === 'success' && <CheckCircle2 className="text-emerald-400" size={36} />}
                {status === 'error' && <AlertCircle className="text-red-400" size={36} />}
                
                <p className={`font-medium text-lg ${status === 'loading' ? 'text-indigo-200' : status === 'success' ? 'text-emerald-200' : 'text-red-200'}`}>{message}</p>
                
                {status === 'success' && resultUrl && (
                  <div className="pt-4 w-full"><a href={resultUrl} target="_blank" rel="noopener noreferrer" download className="inline-flex items-center justify-center w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 px-6 rounded-xl transition-all shadow-lg shadow-emerald-900/50 hover:scale-[1.02] active:scale-[0.98] space-x-2 text-lg"><Download size={20} /><span>Zapisz Plik na Dysk</span></a></div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
