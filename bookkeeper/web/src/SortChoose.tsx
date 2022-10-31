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
}

interface ISortedRequest {
  sorted: Array<IDirectiveMod>;
}

export default function SortChoose() {
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");
  // "unsorted" and "sorted" are mutually exclusive. A txn is moved from one to the
  //  other as it is handled in the UI.
  const [unsorted, setUnsorted] = useState<List<IDirectiveForSort>>(List());
  const [sorted, setSorted] = useState<List<IDirectiveForSort>>(List());
  // "mods" contains a single entry for each txn in "sorted".
  const [mods, setMods] = useState<Map<string, IDirectiveMod>>(Map());

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(NEXT_API);
      const data = (await resp.json()) as INextResponse;
      console.log("GET", data);
      setUnsorted(List(data.to_sort));
    };

    fetchData().catch(errorHandler);
  }, []);

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
    setUnsorted(List(data.to_sort));
    setAsyncProgress("success");
    setTimeout(() => {
      setAsyncProgress("idle");
    }, 5000);
  };

  return (
    <div>
      <p>Actual choose flow</p>
      {unsorted.size > 0 && (
        <Transaction
          txn={unsorted.get(0)!}
          onSort={(newMods) => {
            // Add in the new "mods"
            setMods(mods.concat(newMods.map((mod) => [mod.id, mod])));
            // Update "unsorted" and "sorted"
            const modIDs = Set(newMods.map((mod) => mod.id));
            const modIDsHas = (dir: IDirectiveForSort) => modIDs.has(dir.id);
            setSorted(sorted.concat(unsorted.filter(modIDsHas)));
            setUnsorted(unsorted.filterNot(modIDsHas));
          }}
        />
      )}
      <p className="text-center">
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
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
