import { List, Map as ImmMap } from "immutable";
import React, { useState } from "react";
import { Link } from "react-router-dom";

import { IDirectiveForSort, IDirectiveMod } from "./beanTypes";
import Transaction from "./Transaction";

export default function SortReview() {
  const [sorted, setSorted] = useState<List<IDirectiveForSort>>(List());
  const [mods, setMods] = useState<ImmMap<string, IDirectiveMod>>(ImmMap());

  // Fetch saved txns via API call

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
          }}
        />
      ))}
      <div className="flex justify-between py-4">
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
          <Link to={`/sort/choose`}>Categorise More</Link>
        </button>
      </div>
    </div>
  );
}
