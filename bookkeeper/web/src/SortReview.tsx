import { List, Map as ImmMap } from "immutable";
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { IDirectiveForSort, IDirectiveMod } from "./beanTypes";
import Transaction from "./Transaction";
import { API, errorHandler } from "./utilities";

const SORTED_API = `${API}/sort/sorted`;

interface ISortedResponse {
  sorted: Array<IDirectiveForSort>;
  mods: Record<string, IDirectiveMod>;
}

export default function SortReview() {
  const [sorted, setSorted] = useState<List<IDirectiveForSort>>(List());
  const [mods, setMods] = useState<ImmMap<string, IDirectiveMod>>(ImmMap());

  // Fetch saved txns via API call
  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(SORTED_API);
      const data = (await resp.json()) as ISortedResponse;
      console.log("GET", data);
      setSorted(List(data.sorted));
      setMods(ImmMap(data.mods));
    };

    fetchData().catch(errorHandler);
  }, []);

  const deleteMod = async (txnID: string) => {
    const params = new URLSearchParams();
    params.append("txnID", txnID);
    const url = new URL(SORTED_API);
    url.search = params.toString();
    const resp = await fetch(url, { method: "POST" });
    const data = (await resp.json()) as ISortedResponse;
    console.log("POST", data);
    setSorted(List(data.sorted));
    setMods(ImmMap(data.mods));
  };

  return (
    <div className="max-w-screen-lg mx-auto py-5">
      <header>
        <h2 className="text-2xl">Review Sorted Transactions</h2>
      </header>
      {sorted.map((dir) => (
        <Transaction
          txn={dir}
          key={dir.id}
          priorMod={mods.get(dir.id)!}
          editable={false}
          onRevert={(txnID) => {
            // Delete this mod via an API call
            deleteMod(txnID).catch(errorHandler);
          }}
        />
      ))}
      <div className="flex justify-between py-4">
        <button
          className="ml-2 border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          type="button"
        >
          <Link to={`/sort/choose`}>Categorise More</Link>
        </button>
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          type="button"
        >
          <Link to={`/sort/commit`}>Commit</Link>
        </button>
      </div>
    </div>
  );
}
