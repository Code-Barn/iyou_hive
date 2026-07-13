import React from "react";

interface HeaderProps {
  username: string;
}

export const SovereignHeader: React.FC<HeaderProps> = ({ username }) => {
  return (
    <header className="w-full border-b border-slate-800 bg-slate-900 text-slate-100 px-6 py-3 flex items-center justify-between font-mono text-sm shadow-sm pt-5">
      <div className="flex items-center space-x-2">
        <span className="font-bold tracking-tight text-orange-400">iyou_</span>
        <span className="text-slate-400 font-semibold">hive</span>
      </div>

      <div className="flex items-center space-x-4 text-xs">
        <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1 rounded border border-slate-700">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-slate-300 font-bold" title={username}>
            {username}
          </span>
        </div>
        <a
          href="/oidc/logout/"
          className="text-slate-400 hover:text-rose-500 transition-colors duration-150"
        >
          Sign Out
        </a>
      </div>
    </header>
  );
};

export default SovereignHeader;
