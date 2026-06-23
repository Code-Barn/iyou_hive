import React from "react";

function getCSRFToken(): string {
  const name = "hiver_csrftoken";
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        return decodeURIComponent(cookie.substring(name.length + 1))
          .replace(/^["']|["']$/g, "")
          .trim();
      }
    }
  }
  return "";
}

interface SovereignHeaderProps {
  username?: string;
  appPrefix?: string;
}

const SovereignHeader: React.FC<SovereignHeaderProps> = ({
  username,
  appPrefix = "mesh",
}) => {
  const handleLogout = () => {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "/oidc/logout/";
    const csrf = document.createElement("input");
    csrf.type = "hidden";
    csrf.name = "csrfmiddlewaretoken";
    csrf.value = getCSRFToken();
    form.appendChild(csrf);
    document.body.appendChild(form);
    form.submit();
  };

  return (
    <header className="w-full border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-6 py-3 flex items-center justify-between font-mono text-sm shadow-sm pt-5">
      <div className="flex items-center space-x-2">
        <span className="font-bold tracking-tight text-purple-600 dark:text-purple-400">
          iyou_
        </span>
        <span className="text-slate-500 font-semibold">{appPrefix}</span>
      </div>

      <div className="flex items-center space-x-4 text-xs">
        {username ? (
          <>
            <div className="flex items-center space-x-2 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded border border-slate-200 dark:border-slate-700">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span
                className="text-slate-600 dark:text-slate-300 max-w-[240px] truncate"
                title={username}
              >
                {username}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-rose-500 transition-colors duration-150 bg-transparent border-none cursor-pointer"
            >
              Sign Out
            </button>
          </>
        ) : (
          <>
            <div className="flex items-center space-x-2">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-slate-400 italic">
                Sovereign Key Required
              </span>
            </div>
            <a
              href="/oidc/authenticate/"
              className="bg-purple-600 hover:bg-purple-500 text-white font-bold px-3 py-1 rounded transition-colors duration-150 shadow-sm"
            >
              Sign In
            </a>
          </>
        )}
      </div>
    </header>
  );
};

export default SovereignHeader;
