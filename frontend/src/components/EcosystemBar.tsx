import React from "react";

export const EcosystemBar: React.FC = () => {
  return (
    <div
      id="sovereign-ecosystem-topbar"
      className="fixed top-0 left-0 w-full z-[9999] transform -translate-y-[calc(100%-4px)] hover:translate-y-0 transition-all duration-300 ease-in-out bg-slate-950 border-b border-orange-600/50 text-slate-400 px-4 py-1.5 shadow-2xl flex items-center space-x-6 text-[11px] font-mono"
    >
      <span className="text-orange-400 font-bold tracking-wider uppercase">
        🌌 SOVEREIGN MESH:
      </span>
      <div className="flex items-center space-x-4">
        <a href="https://iyou.me" className="hover:text-white transition-colors duration-150">
          idp
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://wun.iyou.me" className="hover:text-white transition-colors duration-150">
          wun
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://poly.iyou.me" className="hover:text-white transition-colors duration-150">
          poly
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://name.iyou.me" className="hover:text-white transition-colors duration-150">
          name
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://hive.iyou.me" className="text-white font-bold tracking-normal">
          hive
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://ride.iyou.me" className="hover:text-white transition-colors duration-150">
          ride
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://dctech.iyou.me" className="hover:text-white transition-colors duration-150">
          dctech
        </a>
        <span className="text-slate-800">/</span>
        <a href="https://safe.iyou.me" className="hover:text-white transition-colors duration-150">
          safe
        </a>
      </div>
    </div>
  );
};

export default EcosystemBar;
