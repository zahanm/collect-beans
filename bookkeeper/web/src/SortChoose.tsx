import React, { useEffect } from "react";
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

function SortChoose() {
  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(NEXT_API, {
        headers: {
          Accept: "application/json",
        },
      });
      const data = (await resp.json()) as INextResponse;
      console.log("GET", data);
    };

    fetchData().catch(errorHandler);
  }, []);

  return (
    <div>
      <p>Actual choose flow</p>
      <Link to={`/sort/commit`} className="text-sky-400">
        Commit
      </Link>
    </div>
  );
}

export default SortChoose;
