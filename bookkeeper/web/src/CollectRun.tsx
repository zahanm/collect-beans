import dayjs from "dayjs";
import React, { useState } from "react";

import { CollectMode } from "./beanTypes";
import { API, errorHandler } from "./utilities";

export interface SecretsSchema {
  importers: Array<ImporterSchema>;
}
interface ImporterSchema {
  name: string;
  access_token: string;
  institution_id: string;
  accounts: Array<AccountSchema>;
}
interface AccountSchema {
  name: string;
  plaid_id: string;
}

const RUN_API = `${API}/collect/run`;
interface IRunResponse {
  returncode: number;
  errors: Array<string>;
}

export default function CollectRun(props: {
  mode: CollectMode;
  secrets: SecretsSchema;
}) {
  const { mode, secrets } = props;

  const [startDate, setStartDate] = useState<string>(
    dayjs().subtract(30, "days").format("YYYY-MM-DD")
  );
  const [endDate, setEndDate] = useState<string>(dayjs().format("YYYY-MM-DD"));
  const [errors, setErrors] = useState<Array<string>>([]);

  const runImporter = async (importer: ImporterSchema) => {
    const body = {
      start: startDate,
      end: endDate,
      mode,
      importer,
    };
    const resp = await fetch(RUN_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const data = (await resp.json()) as IRunResponse;
    console.log("POST", data);
    if (data.returncode != 0) {
      setErrors(data.errors);
    }
  };

  return (
    <div>
      <p className="p-4">
        We're running in <strong>{mode}</strong> mode
      </p>
      <div className="p-4">
        <Config
          start={startDate}
          onChangeStart={(s) => setStartDate(s)}
          end={endDate}
          onChangeEnd={(e) => setEndDate(e)}
        />
      </div>
      <p className="p-4">We have {secrets.importers.length} importers</p>
      {errors.length > 0 ? <Errors errors={errors} /> : null}
      <div className="grid grid-cols-2">
        {secrets.importers.map((imp) => (
          <Importer
            imp={imp}
            runner={(imp) => runImporter(imp).catch(errorHandler)}
            key={imp.name}
          />
        ))}
      </div>
    </div>
  );
}

function Config(props: {
  start: string;
  onChangeStart: (s: string) => void;
  end: string;
  onChangeEnd: (s: string) => void;
}) {
  return (
    <>
      <h2 className="text-lg">Options</h2>
      <div className="grid grid-cols-2">
        <div>
          <p className="py-1">
            <label htmlFor="start_from" className="mr-1">
              Start
            </label>
            <input
              type="date"
              name="start_from"
              value={props.start}
              onChange={(ev) => props.onChangeStart(ev.target.value)}
              required
              className="text-black px-2"
            />
          </p>
          <p className="py-1">
            <label htmlFor="end_on" className="mr-1">
              End
            </label>
            <input
              type="date"
              name="end_on"
              value={props.end}
              onChange={(ev) => props.onChangeEnd(ev.target.value)}
              required
              className="text-black px-2"
            />
          </p>
          <p className="py-1">
            <label htmlFor="skip_status" className="mr-1">
              Should skip institution status check
            </label>
            <select name="skip_status" defaultValue="no" className="text-black">
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </p>
        </div>
        <div className="flex items-center">
          <button className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black">
            Run all
          </button>
        </div>
      </div>
    </>
  );
}

function Importer(props: {
  imp: ImporterSchema;
  runner: (i: ImporterSchema) => void;
}) {
  const { imp } = props;
  return (
    <div className="border-solid border-2 rounded-lg p-4 m-1 relative">
      <h3>{imp.name}</h3>
      <p>
        Instituition ID: <code>{imp.institution_id}</code>
      </p>
      <p>
        Access token: <code>{imp.access_token || "None"}</code>
      </p>
      <p>
        {imp.accounts.length} account{imp.accounts.length > 1 ? "s" : ""}
      </p>
      {imp.accounts.map((acc) => (
        <p className="pl-2" key={acc.name}>
          <code>{acc.name}</code>
        </p>
      ))}
      <button
        type="button"
        className="absolute top-1 right-1 p-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black"
        onClick={() => props.runner(imp)}
      >
        Run
      </button>
    </div>
  );
}

function Errors(props: { errors: Array<string> }) {
  return (
    <div className="p-4 bg-red-300">
      {props.errors.map((error) => (
        <span className="text-red-600" key={error}>
          {error}
        </span>
      ))}
    </div>
  );
}
