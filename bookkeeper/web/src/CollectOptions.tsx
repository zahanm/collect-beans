import dayjs from "dayjs";
import React, { useState } from "react";
import { Link } from "react-router-dom";

import DisplayProgress, { TProgress } from "./DisplayProgress";
import { API, errorHandler } from "./utilities";

const OPTIONS_API = `${API}/collect/options`;

interface IOptionsResponse {
  collect_mode: string | null;
  start_date: string | null;
}

export default function CollectOptions() {
  const [asyncProgress, setAsyncProgress] = useState<TProgress>("idle");
  const [collectMode, setCollectMode] = useState<string>("transactions");
  const [startDate, setStartDate] = useState<string>(
    dayjs().format("YYYY-MM-DD")
  );

  function setStateFromAPI(data: IOptionsResponse) {
    data.collect_mode && setCollectMode(data.collect_mode);
    data.start_date && setStartDate(data.start_date);
  }

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
            const resp = await fetch(OPTIONS_API, {
              method: "POST",
              body,
            });
            const data = (await resp.json()) as IOptionsResponse;
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
          <label htmlFor="collect_mode" className="mr-1">
            Collect mode:
          </label>
          <select
            name="collect_mode"
            defaultValue={collectMode}
            required
            className="text-black"
          >
            <option value="balance">Balance</option>
            <option value="transactions">Transactions</option>
          </select>
        </p>
        <p className="py-1">
          <label htmlFor="start_from" className="mr-1">
            Starting date:
          </label>
          <input
            type="date"
            name="start_from"
            defaultValue={startDate}
            required
            className="text-black"
          ></input>
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
        <Link to={`/collect/choose`} className="text-sky-400">
          Start
        </Link>
      </div>
    </div>
  );
}
