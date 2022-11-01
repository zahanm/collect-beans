import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { List, Map, Set } from "immutable";

import { IDirectiveForSort, IDirectiveMod } from "./beanTypes";
import Transaction from "./Transaction";
import DisplayProgress, { TProgress } from "./DisplayProgress";
import { errorHandler } from "./utilities";

const NEXT_API = "http://localhost:5005/next_sort";

interface INextResponse {
  to_sort: Array<IDirectiveForSort>;
  accounts: Array<string>;
}

interface ISortedRequest {
  sorted: Array<IDirectiveMod>;
}

const MAX_TXNS = 20;

export default function SortChoose() {
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");
  // "unsorted" and "sorted" are mutually exclusive. A txn is moved from one to the
  //  other as it is handled in the UI.
  const [unsorted, setUnsorted] = useState<List<IDirectiveForSort>>(List());
  const [sorted, setSorted] = useState<List<IDirectiveForSort>>(List());
  // "mods" contains a single entry for each txn in "sorted".
  const [mods, setMods] = useState<Map<string, IDirectiveMod>>(Map());
  // "accounts" is used for auto-complete
  const [accounts, setAccounts] = useState<Set<string>>(Set());

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(NEXT_API);
      const data = (await resp.json()) as INextResponse;
      console.log("GET", data);
      const modIds = mods.keySeq().toSet();
      // Can be added to unsorted as long as it's not already sorted locally
      setUnsorted(List(data.to_sort).filterNot((dir) => modIds.has(dir.id)));
      setAccounts(Set(data.accounts));
    };

    if (sorted.size + unsorted.size < MAX_TXNS) {
      fetchData().catch(errorHandler);
    }
  }, [sorted, unsorted, mods]);

  const saveChanges = async () => {
    setAsyncProgress("in-process");
    const body: ISortedRequest = {
      sorted: mods.valueSeq().toArray(),
    };
    const resp = await fetch(NEXT_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const data = (await resp.json()) as INextResponse;
    console.log("POST", data);
    setAsyncProgress("success");
    setTimeout(() => {
      setUnsorted(List(data.to_sort));
      setAccounts(Set(data.accounts));
      setSorted(List());
      setMods(Map());
      setAsyncProgress("idle");
    }, 3000);
  };

  return (
    <div>
      <h2 className="text-2xl">Categorise Transactions</h2>
      {sorted.concat(unsorted).map((dir) => (
        <Transaction
          txn={dir}
          key={dir.id}
          priorMod={mods.get(dir.id, null)}
          accounts={accounts}
          onSave={(newMod) => {
            // Turning this into a list to slightly future-proof the logic for when
            // I have batch operations
            const newMods = [newMod];
            // Add in the new "mods"
            setMods(mods.concat(newMods.map((mod) => [mod.id, mod])));
            // Update "unsorted" and "sorted"
            const modIDs = Set(newMods.map((mod) => mod.id));
            const modIDsHas = (dir: IDirectiveForSort) => modIDs.has(dir.id);
            setSorted(sorted.concat(unsorted.filter(modIDsHas)));
            setUnsorted(unsorted.filterNot(modIDsHas));
          }}
        />
      ))}
      <p className="text-center">
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:opacity-25"
          disabled={mods.size === 0}
          onClick={() =>
            saveChanges().catch((err) => {
              setAsyncProgress("error");
              errorHandler(err);
            })
          }
        >
          Save Changes
        </button>
        <DisplayProgress progress={asyncProgress} className="ml-2" />
      </p>
      <Link to={`/sort`} className="text-sky-400">
        Options
      </Link>
      <Link to={`/sort/commit`} className="text-sky-400 ml-2">
        Commit
      </Link>
    </div>
  );
}
