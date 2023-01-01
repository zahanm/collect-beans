import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import { List } from "immutable";

import { API, errorHandler } from "./utilities";
import DisplayProgress, { TProgress } from "./DisplayProgress";
import NavBar from "./NavBar";

const PROGRESS_API = `${API}/sort/progress`;

interface IProgressResponse {
  journal_files: Array<string>;
  main_file: string | null;
  destination_file: string | null;
  expense_accounts: Array<string>;
}

export default function SortOptions() {
  const [journalFiles, setJournalFiles] = useState<List<string>>(List());
  const [destFile, setDestFile] = useState<string>();
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");

  function setStateFromAPI(data: IProgressResponse) {
    const journalFiles = List(data.journal_files).sort();
    setJournalFiles(journalFiles);
    if (data.destination_file) {
      setDestFile(data.destination_file);
    } else {
      const thisYear = `${dayjs().year()}.beancount`;
      if (journalFiles.contains(thisYear)) {
        setDestFile(thisYear);
      }
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(PROGRESS_API);
      const data = (await resp.json()) as IProgressResponse;
      console.log("GET", data);
      setStateFromAPI(data);
    };

    fetchData().catch(errorHandler);
  }, []);
  // The empty array of dependencies is important. It tells the
  // effect to only run once.

  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h2 className="text-xl">Start Sort</h2>
      <form
        className="my-2"
        onSubmit={(ev) => {
          ev.preventDefault();
          console.log("submitting form", ev);
          setAsyncProgress("in-process");
          const sendData = async () => {
            console.log("sending data");
            const body = new FormData(ev.target as HTMLFormElement);
            const resp = await fetch(PROGRESS_API, {
              method: "POST",
              body,
            });
            const data = (await resp.json()) as IProgressResponse;
            console.log("POST", data);
            setStateFromAPI(data);
            setAsyncProgress("success");
          };

          sendData().catch((err) => {
            setAsyncProgress("error");
            errorHandler(err);
          });
        }}
      >
        <p className="py-1">
          <label htmlFor="destination_file" className="mr-1">
            Destination file:
          </label>
          <select
            name="destination_file"
            value={destFile}
            onChange={(ev) => setDestFile(ev.target.value)}
            required
            className="text-black"
          >
            {journalFiles.map((f) => (
              <option value={f} key={f}>
                {f}
              </option>
            ))}
          </select>
        </p>
        <p className="text-center">
          <button
            type="submit"
            className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          >
            Save in-memory
          </button>
          <DisplayProgress progress={asyncProgress} className="ml-2" />
          <Link to={`/sort/choose`} className="ml-2">
            <button
              type="button"
              className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
            >
              Start
            </button>
          </Link>
        </p>
      </form>
      <NavBar />
    </div>
  );
}
