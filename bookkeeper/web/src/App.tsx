import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BanknotesIcon } from "@heroicons/react/24/outline";

import DisplayProgress, { TProgress } from "./DisplayProgress";
import { API, errorHandler } from "./utilities";

const RELOAD_API = `${API}/config/reload`;
interface IReloadResponse {
  success: boolean;
}

function App() {
  const [reloadProgress, setReloadProgress] = useState<TProgress>("idle");

  useEffect(() => {
    const runReload = async () => {
      const resp = await fetch(RELOAD_API, {
        method: "POST",
      });
      const data = (await resp.json()) as IReloadResponse;
      console.log("POST", data);
      if (data.success) {
        setReloadProgress("success");
        setTimeout(() => setReloadProgress("idle"), 10 * 1000);
      } else {
        setReloadProgress("error");
      }
    };

    if (reloadProgress === "in-process") {
      runReload().catch(errorHandler);
    }
  }, [reloadProgress]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-2xl">
      <h2 className="text-5xl">Collecting Beans</h2>
      <BanknotesIcon className="w-[30vmin] h-[30vmin] animate-pulse" />
      <p>
        The following will update <code>data/*.beancount</code> when complete.
      </p>
      <Link to={`collect`} className="my-1">
        <button className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black">
          Collect New
        </button>
      </Link>
      <Link to={`sort`} className="my-1">
        <button className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black">
          Sort Transactions
        </button>
      </Link>
      <section className="my-1">
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          onClick={() => setReloadProgress("in-process")}
        >
          Reload Config
        </button>
        <DisplayProgress progress={reloadProgress} className="m-1" />
      </section>
    </div>
  );
}

export default App;
