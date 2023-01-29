import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { List, Map as ImmMap } from "immutable";
import React, { useEffect, useState } from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer";

import { CollectMode } from "./beanTypes";
import DisplayProgress, { TProgress } from "./DisplayProgress";
import NavBar from "./NavBar";
import { API, errorHandler } from "./utilities";

dayjs.extend(relativeTime);

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
  currency: string;
}

const RUN_API = `${API}/collect/run`;
interface IRunResponse {
  returncode: number;
  errors: Array<string>;
}

const LAST_IMPORTED_API = `${API}/collect/last-imported`;
interface ILastImportedResponse {
  last: { [k: string]: string };
}

const OTHER_IMPORTERS_API = `${API}/collect/other-importers`;
interface IOtherImportersResponse {
  importers: Array<OtherImporterSchema>;
}
interface OtherImporterSchema {
  name: string;
  downloader: string;
  importer?: string;
  instructions?: string;
  accounts: Array<OtherAccountSchema>;
}
interface OtherAccountSchema {
  name: string;
  currency: string;
}

const OVERLAP_IMPORT_DAYS = 1;

export default function CollectRun(props: {
  mode: CollectMode;
  secrets: SecretsSchema;
}) {
  const { mode, secrets } = props;

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
  const [otherImporters, setOtherImporters] = useState<
    List<OtherImporterSchema>
  >(List());

  const thirtyDaysAgo = dayjs().subtract(30, "days").format("YYYY-MM-DD");
  // Map { importer name -> start date in YYYY-MM-DD }
  const [startDates, setStartDates] = useState<ImmMap<string, string>>(
    ImmMap(secrets.importers.map((imp) => [imp.name, thirtyDaysAgo]))
  );

  const runImporter = async (importer: ImporterSchema) => {
    if (runProgress.get(importer.name) === "error") {
      // Skip running an error'd importer
      return;
    }
    setRunProgress((rp) => rp.set(importer.name, "in-process"));
    const body = {
      start: startDates.get(importer.name)!,
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
    const fetchOtherImporters = async () => {
      const params = new URLSearchParams();
      params.set("mode", mode);
      const url = new URL(OTHER_IMPORTERS_API);
      url.search = params.toString();
      const resp = await fetch(url);
      const data = (await resp.json()) as IOtherImportersResponse;
      console.log("GET", data);
      setOtherImporters(List(data.importers));
    };

    fetchOtherImporters().catch(errorHandler);
  }, [mode]);

  useEffect(() => {
    const fetchLastImported = async () => {
      const params = new URLSearchParams();
      otherImporters
        .concat(secrets.importers)
        .forEach((imp) =>
          imp.accounts.forEach((acc) => params.append("accounts", acc.name))
        );
      const url = new URL(LAST_IMPORTED_API);
      url.search = params.toString();
      const resp = await fetch(url);
      const data = (await resp.json()) as ILastImportedResponse;
      console.log("GET", data);
      setLastImported((last) => last.merge(data.last));
      // Set startDates to the oldest last-import for an account in that importer
      setStartDates((sds) =>
        sds.map((_, impname) => {
          const importer = secrets.importers.find(
            (imp) => imp.name === impname
          )!;
          const oldestLastImport = List(importer.accounts)
            .map((acc) => data.last[acc.name])
            .filter((v) => !!v)
            .min();
          return oldestLastImport
            ? dayjs(oldestLastImport)
                .subtract(OVERLAP_IMPORT_DAYS, "days")
                .format("YYYY-MM-DD")
            : thirtyDaysAgo;
        })
      );
    };

    fetchLastImported().catch(errorHandler);
  }, [otherImporters, secrets.importers, thirtyDaysAgo]);

  const anyImporterRunning = runProgress
    .valueSeq()
    .some((p) => p === "in-process");

  return (
    <div>
      <p className="p-4">
        We're running in <strong>{mode}</strong> mode
      </p>
      <div className="p-4">
        <Backup anyimporterrunning={anyImporterRunning} />
      </div>
      <div className="p-4">
        <Config
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
            start={startDates.get(imp.name)!}
            onChangeStart={(d) => setStartDates((sds) => sds.set(imp.name, d))}
            anyimporterrunning={anyImporterRunning}
          />
        ))}
      </div>
      <hr />
      <p className="p-4">We have {otherImporters.size} other importers</p>
      <div className="grid grid-cols-2">
        {otherImporters.map((imp) => (
          <OtherImporter imp={imp} key={imp.name} lastimported={lastImported} />
        ))}
      </div>
      <NavBar />
    </div>
  );
}

const BACKUP_API = `${API}/collect/backup`;
interface IBackupResponse {
  contents: {
    old: string;
    new: string;
  };
  timestamps: {
    last_backup: number;
  };
}

function Backup(props: { anyimporterrunning: boolean }) {
  const [showDiff, setShowDiff] = useState<boolean>(false);
  const [before, setBefore] = useState<string>();
  const [after, setAfter] = useState<string>();
  const [bkpProgress, setBkpProgress] = useState<TProgress>("idle");
  const [lastBackup, setLastBackup] = useState<number>();

  function setDiff(newbefore: string, newafter: string, last: number) {
    setBefore(newbefore);
    setAfter(newafter);
    setLastBackup(last);
  }

  useEffect(() => {
    const fetchDiff = async () => {
      const resp = await fetch(BACKUP_API);
      const data = (await resp.json()) as IBackupResponse;
      console.log("GET", data);
      setDiff(
        data.contents.old,
        data.contents.new,
        data.timestamps.last_backup
      );
    };

    if (bkpProgress !== "in-process") {
      fetchDiff().catch(errorHandler);
    }
  }, [showDiff, bkpProgress, props.anyimporterrunning]);

  useEffect(() => {
    const runBackup = async () => {
      const resp = await fetch(BACKUP_API, {
        method: "POST",
      });
      const data = (await resp.json()) as IBackupResponse;
      console.log("POST", data);
      setDiff(
        data.contents.old,
        data.contents.new,
        data.timestamps.last_backup
      );
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
          className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black disabled:text-gray-400 disabled:border-gray-400"
          onClick={() => setShowDiff((show) => !show)}
          disabled={!showDiff && before === after}
        >
          {showDiff ? "Hide diff" : before === after ? "No diff" : "View diff"}
        </button>
        <span className="ml-3">
          <button
            className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black"
            onClick={() => setBkpProgress("in-process")}
          >
            Run backup
          </button>
          <DisplayProgress progress={bkpProgress} className="m-1" />
        </span>
        {lastBackup && (
          <span className="ml-3">{dayjs.unix(lastBackup).fromNow()}</span>
        )}
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
            <label htmlFor="end_on" className="mr-1">
              End on
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
  start: string;
  onChangeStart: (d: string) => void;
  anyimporterrunning: boolean;
}) {
  const { imp } = props;
  return (
    <div className="border-solid border-2 rounded-lg p-4 m-1 relative">
      <h3 className="text-pink-200">{imp.name}</h3>
      <p>
        Instituition ID: <code>{imp.institution_id}</code>
      </p>
      <p className="whitespace-nowrap overflow-x-auto">
        Access token:{" "}
        <code className="text-sky-200">{imp.access_token || "None"}</code>
      </p>
      <p>
        {imp.accounts.length} account{imp.accounts.length > 1 ? "s" : ""}
      </p>
      {imp.accounts.map((acc) => (
        <Account
          account={acc}
          lastimported={props.lastimported}
          key={acc.name}
        />
      ))}
      <span className="absolute top-1 right-1">
        <input
          type="date"
          name="start_from"
          value={props.start}
          onChange={(ev) => props.onChangeStart(ev.target.value)}
          required
          className="bg-slate-300 text-black p-1 w-[12ch] mr-2 border-solid border-2 rounded-lg"
          disabled={props.anyimporterrunning}
        />
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
            disabled={props.anyimporterrunning}
          >
            Run
          </button>
        )}
      </span>
    </div>
  );
}

function OtherImporter(props: {
  imp: OtherImporterSchema;
  lastimported: ImmMap<string, string>;
}) {
  const { imp } = props;
  return (
    <div className="border-solid border-2 rounded-lg p-4 m-1 relative">
      <h3 className="text-pink-200">{imp.name}</h3>
      <p>Downloader: {imp.downloader}</p>
      {imp.importer && <p>Importer: {imp.importer}</p>}
      {imp.instructions && (
        <p className="overflow-x-auto text-sky-200">{imp.instructions}</p>
      )}
      <p>
        {imp.accounts.length} account{imp.accounts.length > 1 ? "s" : ""}
      </p>
      {imp.accounts.map((acc) => (
        <Account
          account={acc}
          lastimported={props.lastimported}
          key={acc.name}
        />
      ))}
    </div>
  );
}

function Account(props: {
  account: AccountSchema | OtherAccountSchema;
  lastimported: ImmMap<string, string>;
}) {
  const { account, lastimported } = props;
  return (
    <p className="pl-2 flex justify-between">
      <code
        className={`text-green-300 whitespace-nowrap overflow-x-auto ${
          lastimported.get(account.name) ? "max-w-[77%]" : ""
        }`}
      >
        {account.name}
      </code>
      {lastimported.get(account.name) && (
        <span className="text-amber-200">{lastimported.get(account.name)}</span>
      )}
    </p>
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
