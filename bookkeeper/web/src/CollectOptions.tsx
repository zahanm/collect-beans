import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { CollectMode } from "./beanTypes";
import { API, errorHandler, invariant } from "./utilities";

export default function CollectOptions(props: {
  onSecretsSubmit: (m: CollectMode, s: string) => void;
}) {
  const [collectMode, setCollectMode] = useState<CollectMode>("transactions");
  const [copyComplete, setCopyComplete] = useState(false);

  const copyRef = useRef<HTMLInputElement>(null);
  const pasteRef = useRef<HTMLInputElement>(null);

  const params = new URLSearchParams();
  params.append("mode", collectMode);
  const url = new URL(`${API}/collect.py`);
  url.search = params.toString();

  const copyCommand = async () => {
    if (copyRef.current) {
      copyRef.current.focus();
      await navigator.clipboard.writeText(copyRef.current.value);
      setCopyComplete(true);
      setTimeout(() => setCopyComplete(false), 5 * 1000);
    }
  };

  const pasteOutput = async () => {
    if (pasteRef.current) {
      pasteRef.current.value = await navigator.clipboard.readText();
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h2 className="text-xl">Start Sort</h2>
      <form
        className="my-2"
        onSubmit={(ev) => {
          ev.preventDefault();
          console.log("submitting form", ev, collectMode);
          invariant(pasteRef.current);
          props.onSecretsSubmit(collectMode, pasteRef.current!.value);
        }}
      >
        <p className="py-1">
          <label htmlFor="collect_mode" className="mr-1">
            Collect mode
          </label>
          <select
            name="collect_mode"
            value={collectMode}
            onChange={(ev) => setCollectMode(ev.target.value as CollectMode)}
            required
            className="text-black"
          >
            <option value="balance">Balance</option>
            <option value="transactions">Transactions</option>
          </select>
        </p>
        <p className="py-1">
          <input
            type="text"
            className="font-mono w-[84ch] text-black p-1"
            name="copy"
            value={`python3 <(curl --silent "${url}")`}
            readOnly={true}
            onFocus={(ev) => ev.target.select()}
            ref={copyRef}
          />
          {window.isSecureContext && (
            <button
              className={`${
                copyComplete ? "ml-[-68px]" : "ml-[-50px]"
              } bg-slate-700 px-1 border-solid border-2 rounded-md hover:bg-white hover:text-black`}
              type="button"
              onClick={() => copyCommand().catch(errorHandler)}
              disabled={copyComplete}
            >
              {copyComplete ? "copied!" : "copy"}
            </button>
          )}
        </p>
        <p className="py-1">
          <input
            type="text"
            className="font-mono w-[84ch] text-black p-1 overflow-x-hidden"
            name="localsecrets"
            placeholder="Paste the output from the script here"
            ref={pasteRef}
          />
          {window.isSecureContext && (
            <button
              className="ml-[-54px] bg-slate-700 px-1 border-solid border-2 rounded-md hover:bg-white hover:text-black"
              type="button"
              onClick={() => pasteOutput().catch(errorHandler)}
            >
              paste
            </button>
          )}
        </p>
        <p className="text-center">
          <button
            type="submit"
            className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          >
            Continue
          </button>
        </p>
      </form>
      <div className="mt-2">
        <Link to={`/`} className="text-sky-400">
          Cancel
        </Link>
      </div>
    </div>
  );
}
