/*
 * Copyright (C) 2026 Byers Brands, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

import React, { useEffect, useState } from "react";

/**
 * Read the ``hiver_csrftoken`` cookie and return its raw value,
 * stripped of any surrounding quotation marks, whitespace, or
 * URL-encoding artifacts that would cause a
 * "CSRF token from the 'X-Csrftoken' HTTP header has incorrect length"
 * rejection from Django's ``CsrfViewMiddleware``.
 */
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

const SovereignHeader: React.FC = () => {
  const [meshActive, setMeshActive] = useState(false);

  const root = document.getElementById("timeline-app");
  const vaultUrl = root?.dataset?.vaultUrl || "wss://home.iyou.me:9001/";
  const polyUrl = root?.dataset?.polyUrl || "https://poly.iyou.me";
  const socialfeedUrl = root?.dataset?.socialfeedUrl || "https://wun.iyou.me";

  useEffect(() => {
    const httpUrl = vaultUrl.replace(/^ws:/, "http:").replace(/^wss:/, "https:");
    fetch(httpUrl + "/", { signal: AbortSignal.timeout(300) })
      .then((r) => { if (r.ok) setMeshActive(true); })
      .catch(() => {});
  }, [vaultUrl]);

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

  const username = root?.dataset?.username || "";

  return (
    <nav className="bg-white shadow-sm border-b dark:bg-gray-800 text-sm">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-9">
        <span className="font-bold text-lg text-indigo-600 dark:text-indigo-400">
          Hiver
        </span>
        <div className="flex items-center gap-4">
          <a
            href={socialfeedUrl}
            className="text-gray-600 hover:text-indigo-600 dark:text-gray-300 dark:hover:text-indigo-400"
          >
            Social Feed
          </a>
          <a
            href={polyUrl}
            className="text-gray-600 hover:text-indigo-600 dark:text-gray-300 dark:hover:text-indigo-400"
          >
            Poly
          </a>
          {username && (
            <span
              className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full font-medium dark:bg-purple-900 dark:text-purple-200"
              title={username}
            >
              {username.length > 24 ? username.slice(0, 24) + "…" : username}
            </span>
          )}
          <span
            id="meshBadge"
            className={
              "text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full font-medium dark:bg-green-900 dark:text-green-200" +
              (meshActive ? "" : " hidden")
            }
          >
            Sovereign Mesh Active
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer dark:text-red-400 dark:hover:text-red-300"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

export default SovereignHeader;
