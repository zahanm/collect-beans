import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { List, Map as ImmMap, Set } from "immutable";
import { CircularProgressbarWithChildren } from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";

import { IDirectiveForSort, IDirectiveMod } from "./beanTypes";
import Transaction from "./Transaction";
import DisplayProgress, { TProgress } from "./DisplayProgress";
import { API, errorHandler } from "./utilities";
import NavBar from "./NavBar";

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
      setUnsorted((uns) =>
        uns.concat(filterToUnseen(uns, sorted, data.to_sort))
      );
      setAccounts(Set(data.accounts));
      setTotalToSort(data.count_total);
      setNumSorted(data.count_sorted + sorted.size);
    };

    fetchData().catch(errorHandler);
  }, [mods, sorted]);

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
      setUnsorted(
        unsorted.concat(filterToUnseen(unsorted, sorted, data.to_sort))
      );
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
    setUnsorted(
      // Need to check that we aren't adding dupe transactions to the list.
      filterToUnseen(unsorted, sorted, data.results).concat(unsorted)
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
              {totalToSort - numSorted}/{totalToSort} &#x23F3; {percentFmted}%
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
          postingsEdit={false}
          onSave={(newMod) => {
            setMods(mods.set(newMod.id, newMod));
          }}
          onRevert={(txnID) => {
            // Remove the "mod"
            setMods(mods.remove(txnID));
            const sidx = sorted.findIndex((dir) => dir.id === txnID);
            const txn = sorted.get(sidx)!;
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
          postingsEdit={true}
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
      <NavBar />
    </div>
  );
}

function filterToUnseen(
  unsorted: List<IDirectiveForSort>,
  sorted: List<IDirectiveForSort>,
  newTxns: Array<IDirectiveForSort>
): List<IDirectiveForSort> {
  const seenIDs = unsorted
    .concat(sorted)
    .map((drs) => drs.id)
    .toSet();
  return List(newTxns).filterNot((dir) => seenIDs.has(dir.id));
}
