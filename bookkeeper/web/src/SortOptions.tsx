import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { errorHandler } from "./utilities";
import DisplayProgress, { TProgress } from "./DisplayProgress";

const PROGRESS_API = "http://localhost:5005/progress";
interface IProgressResponse {
  journal_files: Array<string>;
  main_file: string | null;
  destination_file: string | null;
  expense_accounts: Array<string>;
}

function SortOptions() {
  const [journalFiles, setJournalFiles] = useState<Array<string>>([]);
  const [mainFile, setMainFile] = useState<string>();
  const [destFile, setDestFile] = useState<string>();
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");

  function setStateFromAPI(data: IProgressResponse) {
    setJournalFiles(data.journal_files);
    data.main_file && setMainFile(data.main_file);
    data.destination_file && setDestFile(data.destination_file);
  }

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(PROGRESS_API, {
        headers: {
          Accept: "application/json",
        },
      });
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
              headers: {
                Accept: "application/json",
              },
              body,
            });
            const data = (await resp.json()) as IProgressResponse;
            console.log("POST response", data);
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
          <label htmlFor="main_file" className="mr-1">
            Main file:
          </label>
          <select
            name="main_file"
            value={mainFile}
            onChange={(ev) => setMainFile(ev.target.value)}
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
        </p>
      </form>
      <div className="mt-2">
        <Link to={`/`} className="text-sky-400 mr-10">
          Cancel
        </Link>
        <Link to={`/sort/choose`} className="text-sky-400">
          Start
        </Link>
      </div>
    </div>
  );
}

export default SortOptions;
