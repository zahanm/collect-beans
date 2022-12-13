import dayjs from "dayjs";
import { List, Map as ImmMap } from "immutable";
import React, { useEffect, useState } from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer";

import { CollectMode } from "./beanTypes";
import DisplayProgress, { TProgress } from "./DisplayProgress";
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

const LAST_IMPORTED_API = `${API}/collect/last-imported`;
interface ILastImportedResponse {
  last: Record<string, string>;
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
  // Map { importer name -> import progress }
  const [runProgress, setRunProgress] = useState<ImmMap<string, TProgress>>(
    ImmMap()
  );
  // Map { importer name -> list of errors }
  const [errors, setErrors] = useState<ImmMap<string, List<string>>>(ImmMap());
  // Map { account name -> last import date in YYYY-MM-DD }
  const [lastImported, setLastImported] = useState<ImmMap<string, string>>(
    ImmMap()
  );

  const runImporter = async (importer: ImporterSchema) => {
    if (runProgress.get(importer.name) === "error") {
      // Skip running an error'd importer
      return;
    }
    setRunProgress((rp) => rp.set(importer.name, "in-process"));
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
    if (data.returncode !== 0) {
      setErrors((errs) => errs.set(importer.name, List(data.errors)));
      setRunProgress((rp) => rp.set(importer.name, "error"));
    } else {
      setRunProgress((rp) => rp.set(importer.name, "success"));
      setTimeout(() => {
        setRunProgress((rp) => rp.remove(importer.name));
      }, 10 * 1000);
    }
  };

  const runAllImporters = async () => {
    // Run them serially
    for (const importer of secrets.importers) {
      await runImporter(importer);
    }
  };

  useEffect(() => {
    const fetchLastImported = async () => {
      const params = new URLSearchParams();
      secrets.importers.forEach((imp) =>
        imp.accounts.forEach((acc) => params.append("accounts", acc.name))
      );
      const url = new URL(LAST_IMPORTED_API);
      url.search = params.toString();
      const resp = await fetch(url);
      const data = (await resp.json()) as ILastImportedResponse;
      console.log("GET", data);
      setLastImported(ImmMap(data.last));
    };

    fetchLastImported().catch(errorHandler);
  }, []);

  useEffect(() => {
    const oldestLastImported = lastImported
      .valueSeq()
      .filterNot((v) => !!v)
      .min();
    if (oldestLastImported) {
      setStartDate(oldestLastImported);
    }
  }, [lastImported]);

  return (
    <div>
      <p className="p-4">
        We're running in <strong>{mode}</strong> mode
      </p>
      <div className="p-4">
        <Backup />
      </div>
      <div className="p-4">
        <Config
          start={startDate}
          onChangeStart={(s) => setStartDate(s)}
          end={endDate}
          onChangeEnd={(e) => setEndDate(e)}
          onRunAll={() => runAllImporters().catch(errorHandler)}
        />
      </div>
      <p className="p-4">We have {secrets.importers.length} importers</p>
      {errors.size > 0 ? <Errors errors={errors} /> : null}
      <div className="grid grid-cols-2">
        {secrets.importers.map((imp) => (
          <Importer
            imp={imp}
            runner={(imp) => runImporter(imp).catch(errorHandler)}
            runprogress={runProgress.get(imp.name)}
            key={imp.name}
            lastimported={lastImported}
          />
        ))}
      </div>
    </div>
  );
}

const BACKUP_API = `${API}/collect/backup`;
interface IBackupResponse {
  contents: {
    old: string;
    new: string;
  };
}

function Backup() {
  const [showDiff, setShowDiff] = useState<boolean>(false);
  const [before, setBefore] = useState<string>();
  const [after, setAfter] = useState<string>();
  const [bkpProgress, setBkpProgress] = useState<TProgress>("idle");

  function setDiff(newbefore: string, newafter: string) {
    setBefore(newbefore);
    setAfter(newafter);
  }

  useEffect(() => {
    const fetchDiff = async () => {
      const resp = await fetch(BACKUP_API);
      const data = (await resp.json()) as IBackupResponse;
      console.log("GET", data);
      setDiff(data.contents.old, data.contents.new);
    };

    if (showDiff) {
      fetchDiff().catch(errorHandler);
    }
  }, [showDiff]);

  useEffect(() => {
    const runBackup = async () => {
      const resp = await fetch(BACKUP_API, {
        method: "POST",
      });
      const data = (await resp.json()) as IBackupResponse;
      console.log("POST", data);
      setDiff(data.contents.old, data.contents.new);
      setBkpProgress("success");
      setTimeout(() => setBkpProgress("idle"), 10 * 1000);
    };

    if (bkpProgress === "in-process") {
      runBackup().catch(errorHandler);
    }
  }, [bkpProgress]);

  return (
    <>
      <h2 className="text-lg">Backup</h2>
      <p>
        <button
          className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black"
          onClick={() => setShowDiff((show) => !show)}
        >
          {showDiff ? "Hide diff" : "View diff"}
        </button>
        <span>
          <button
            className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black ml-3"
            onClick={() => setBkpProgress("in-process")}
          >
            Run backup
          </button>
          <DisplayProgress progress={bkpProgress} className="m-1" />
        </span>
      </p>
      {showDiff && before && after ? (
        <div className="max-h-[60vh] overflow-y-auto">
          <ReactDiffViewer
            oldValue={before}
            newValue={after}
            splitView={false}
            useDarkTheme={true}
            compareMethod={DiffMethod.LINES}
          />
        </div>
      ) : null}
    </>
  );
}

function Config(props: {
  start: string;
  onChangeStart: (s: string) => void;
  end: string;
  onChangeEnd: (s: string) => void;
  onRunAll: () => void;
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
            <select
              name="skip_status"
              defaultValue="yes"
              className="text-black"
            >
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </p>
        </div>
        <div className="flex items-center">
          <button
            className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black"
            onClick={() => props.onRunAll()}
          >
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
  runprogress: TProgress | undefined;
  lastimported: ImmMap<string, string>;
}) {
  const { imp, lastimported } = props;
  return (
    <div className="border-solid border-2 rounded-lg p-4 m-1 relative">
      <h3 className="text-pink-200">{imp.name}</h3>
      <p>
        Instituition ID: <code>{imp.institution_id}</code>
      </p>
      <p>
        Access token:{" "}
        <code className="text-sky-200">{imp.access_token || "None"}</code>
      </p>
      <p>
        {imp.accounts.length} account{imp.accounts.length > 1 ? "s" : ""}
      </p>
      {imp.accounts.map((acc) => (
        <p className="pl-2" key={acc.name}>
          <code className="text-green-300">{acc.name}</code>
          {lastimported.get(acc.name) && (
            <span className="float-right text-amber-200">
              {lastimported.get(acc.name)}
            </span>
          )}
        </p>
      ))}
      <span className="absolute top-1 right-1">
        {props.runprogress ? (
          <DisplayProgress
            progress={props.runprogress}
            className="inline-block m-1"
          />
        ) : (
          <button
            type="button"
            className="p-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black"
            onClick={() => props.runner(imp)}
          >
            Run
          </button>
        )}
      </span>
    </div>
  );
}

function Errors(props: { errors: ImmMap<string, List<string>> }) {
  return (
    <div className="p-4 bg-red-300">
      {props.errors
        .map((errs, name) => (
          <div key={name}>
            <p className="text-red-900 font-semibold">{name}</p>
            {errs.map((error) => (
              <p className="text-red-600" key={error}>
                {error}
              </p>
            ))}
          </div>
        ))
        .valueSeq()
        .toList()}
    </div>
  );
}
