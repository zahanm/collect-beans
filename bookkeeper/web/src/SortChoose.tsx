import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { List, Map as ImmMap, Set } from "immutable";
import { CircularProgressbarWithChildren } from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";

import { IDirectiveForSort, IDirectiveMod } from "./beanTypes";
import Transaction from "./Transaction";
import DisplayProgress, { TProgress } from "./DisplayProgress";
import { API, errorHandler } from "./utilities";

const NEXT_API = `${API}/sort/next`;
const LINK_API = `${API}/sort/link`;

interface INextResponse {
  to_sort: Array<IDirectiveForSort>;
  accounts: Array<string>;
  count_total: number;
  count_sorted: number;
}

interface ISortedRequest {
  sorted: Array<IDirectiveMod>;
}

interface ILinkResponse {
  results: Array<IDirectiveForSort>;
}

const TAG_SKIP_SORT = "skip-sort";

export default function SortChoose() {
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");
  // "unsorted" and "sorted" are mutually exclusive. A txn is moved from one to the
  //  other as it is handled in the UI.
  const [unsorted, setUnsorted] = useState<List<IDirectiveForSort>>(List());
  const [sorted, setSorted] = useState<List<IDirectiveForSort>>(List());
  // "mods" contains a single entry for each txn in "sorted".
  const [mods, setMods] = useState<ImmMap<string, IDirectiveMod>>(ImmMap());
  // "accounts" is used for auto-complete
  const [accounts, setAccounts] = useState<Set<string>>(Set());
  const [totalToSort, setTotalToSort] = useState<number>(0);
  const [numSorted, setNumSorted] = useState<number>(0);

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(NEXT_API);
      const data = (await resp.json()) as INextResponse;
      console.log("GET", data);
      const modIds = mods.keySeq().toSet();
      // Can be added to unsorted as long as it's not already sorted locally
      setUnsorted(List(data.to_sort).filterNot((dir) => modIds.has(dir.id)));
      setAccounts(Set(data.accounts));
      setTotalToSort(data.count_total);
      setNumSorted(data.count_sorted);
    };

    fetchData().catch(errorHandler);
  }, [mods]);

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
    setTotalToSort(data.count_total);
    setNumSorted(data.count_sorted);
    setTimeout(() => {
      setUnsorted(List(data.to_sort));
      setAccounts(Set(data.accounts));
      setSorted(List());
      setMods(ImmMap());
      setAsyncProgress("idle");
    }, 3000);
  };

  const searchForLinked = async (txnID: string, amount: string) => {
    const params = new URLSearchParams();
    params.append("txnID", txnID);
    params.append("amount", amount);
    const url = new URL(LINK_API);
    url.search = params.toString();
    const resp = await fetch(url);
    const data = (await resp.json()) as ILinkResponse;
    console.log("GET", data);
    const seenIDs = sorted
      .concat(unsorted)
      .map((drs) => drs.id)
      .toSet();
    setUnsorted(
      // Need to check that we aren't adding dupe transactions to the list.
      List(data.results)
        .filter((drs) => !seenIDs.has(drs.id))
        .concat(unsorted)
    );
  };

  const refs = useRef<Map<string, HTMLInputElement>>(new Map());

  useEffect(() => {
    // Focus on the first Transaction, every time the list of Txns is modified
    let res = null;
    const values = refs.current.values();
    do {
      res = values.next();
    } while (!res.value && !res.done);
    const nextVal = res.value;
    nextVal && nextVal.focus();
  }, [unsorted]);

  const percent = (100 * numSorted) / totalToSort;
  const percentFmted = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(percent);

  return (
    <div className="max-w-screen-lg mx-auto py-5">
      <header className="flex justify-between">
        <h2 className="text-2xl">Categorise Transactions</h2>
        <div className="w-20 h-20">
          <CircularProgressbarWithChildren value={percent}>
            <small className="text-center w-1/2">
              {numSorted}/{totalToSort} {percentFmted}%
            </small>
          </CircularProgressbarWithChildren>
        </div>
      </header>
      {sorted.map((dir) => (
        <Transaction
          txn={dir}
          key={dir.id}
          priorMod={mods.get(dir.id)!}
          accounts={accounts}
          editable={false}
          onRevert={(txnID) => {
            // Remove the "mod"
            setMods(mods.remove(txnID));
            const sidx = sorted.findIndex((dir) => dir.id === txnID);
            const txn = sorted.get(sidx)!;
            // Remove the "skip" tag
            const tags = txn.entry.tags;
            const tidx = tags.findIndex((t) => t === TAG_SKIP_SORT);
            if (tidx >= 0) {
              tags.splice(tidx, 1);
            }
            // Put this back in the front of "unsorted", and remove from "sorted"
            setUnsorted(unsorted.unshift(txn));
            setSorted(sorted.remove(sidx));
            setNumSorted(numSorted - 1);
          }}
          onLink={(txnID) => {
            const linker = sorted.find((dir) => dir.id === txnID)!;
            const amount = linker.entry.postings[0].units.number!;
            searchForLinked(linker.id, amount).catch(errorHandler);
          }}
        />
      ))}
      {unsorted.map((dir) => (
        <Transaction
          txn={dir}
          key={dir.id}
          editable={true}
          accounts={accounts}
          ref={refs}
          onSave={(newMod) => {
            // Turning this into a list to slightly future-proof the logic for when
            // I have batch operations
            const newMods = [newMod];
            // Add in the new "mods"
            setMods(mods.concat(newMods.map((mod) => [mod.id, mod])));
            const modIDs = Set(newMods.map((mod) => mod.id));
            const modIDsHas = (dir: IDirectiveForSort) => modIDs.has(dir.id);
            // Add the "skip" tag for the relevant txns
            newMods
              .filter((mod) => mod.type === "skip")
              .forEach((mod) => {
                const skipped = unsorted.find((txn) => txn.id === mod.id)!;
                const tags = skipped.entry.tags;
                if (!(TAG_SKIP_SORT in tags)) {
                  tags.push(TAG_SKIP_SORT);
                }
              });
            // Update "unsorted" and "sorted"
            setSorted(sorted.concat(unsorted.filter(modIDsHas)));
            setUnsorted(unsorted.filterNot(modIDsHas));
            setNumSorted(numSorted + 1);
          }}
        />
      ))}
      <div className="flex justify-between py-4">
        <span>
          <button
            className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
            type="button"
          >
            <Link to={`/sort/commit`}>Commit</Link>
          </button>
          <button
            className="ml-2 border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
            type="button"
          >
            <Link to={`/sort/review`}>Review</Link>
          </button>
        </span>
        <span className="text-center">
          <button
            className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:opacity-25"
            disabled={mods.size === 0}
            type="button"
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
        </span>
      </div>
    </div>
  );
}
