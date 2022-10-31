import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { errorHandler } from "./utilities";

const NEXT_API = "http://localhost:5005/next_sort";

interface INextResponse {
  to_sort: Array<IDirectiveForSort>;
}
interface IDirectiveForSort {
  id: string;
  auto_category: string | null;
  entry: IDirective;
}
interface IDirective {
  date: string;
  filename: string;
  lineno: number;
  payee: string;
  narration: string;
  flag: string;
  tags: Array<string>;
  links: Array<string>;
  postings: Array<IPosting>;
}
interface IPosting {
  account: string;
  units: IAmount;
}
interface IAmount {
  number: string;
  currency: string;
}

interface ISortedRequest {
  sorted: Array<IDirectiveMod>;
}
interface IDirectiveMod {
  // ID of the transaction from IDirectiveToSort
  id: string;
  // Only the _new_ postings that will replace the equity:todo posting.
  postings: Array<IPosting>;
}

export default function SortChoose() {
  // "unsorted" and "sorted" are mutually exclusive. A txn is moved from one to the
  //  other as it is handled in the UI.
  const [unsorted, setUnsorted] = useState<Array<IDirectiveForSort>>([]);
  const [sorted, setSorted] = useState<Array<IDirectiveForSort>>([]);
  // "mods" contains a single entry for each txn in "sorted".
  const [mods, setMods] = useState<Record<string, IDirectiveMod>>({});

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(NEXT_API, {
        headers: {
          Accept: "application/json",
        },
      });
      const data = (await resp.json()) as INextResponse;
      console.log("GET", data);
      setUnsorted(data.to_sort);
    };

    fetchData().catch(errorHandler);
  }, []);

  return (
    <div>
      <p>Actual choose flow</p>
      <Link to={`/sort`} className="text-sky-400">
        Options
      </Link>
      <Link to={`/sort/commit`} className="text-sky-400 ml-2">
        Commit
      </Link>
    </div>
  );
}
