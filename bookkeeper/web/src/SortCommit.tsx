import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer";
import { Map as ImmMap } from "immutable";
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/20/solid";

import { API, errorHandler } from "./utilities";

const COMMIT_API = `${API}/sort/commit`;
const CHECK_API = `${API}/sort/check`;

interface ICommitResponse {
  before: string;
  after: string;
  written: boolean;
}

interface ICheckResponse {
  check: boolean;
  errors: Record<string, string>;
}

export default function SortCommit() {
  const [before, setBefore] = useState<string>();
  const [after, setAfter] = useState<string>();
  const [errors, setErrors] = useState<ImmMap<string, string>>(ImmMap());
  const [checkPassed, setCheckPassed] = useState<boolean>();
  const [written, setWritten] = useState<boolean>(false);

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(COMMIT_API);
      const data = (await resp.json()) as ICommitResponse;
      console.log("GET", data);
      setBefore(data.before);
      setAfter(data.after);
    };

    fetchData().catch(errorHandler);
  }, []);

  const writeChanges = async () => {
    const params = new URLSearchParams();
    params.append("write", "true");
    const url = new URL(COMMIT_API);
    url.search = params.toString();
    const resp = await fetch(url, {
      method: "POST",
    });
    const data = (await resp.json()) as ICommitResponse;
    console.log("POST", data);
    setBefore(data.before);
    setAfter(data.after);
    setWritten(data.written);
  };

  const beanCheck = async () => {
    const resp = await fetch(CHECK_API, {
      method: "POST",
    });
    const data = (await resp.json()) as ICheckResponse;
    console.log("POST", data);
    setCheckPassed(data.check);
    setErrors(ImmMap(data.errors));
  };

  if (written) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center">
        <CheckCircleIcon className="w-20 h-20" />
        <h2 className="text-2xl">
          <Link to={`/`} className="hover:underline">
            Done!
          </Link>
        </h2>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl p-4">Commit the edits</h2>
      {errors.size > 0 && (
        <div className="px-6 py-3 text-red-500 bg-red-200 max-w-full">
          <h2 className="text-xl my-2 font-semibold">
            New edits failed <code>bean-check</code>!
          </h2>
          <pre className="overflow-x-auto">
            {errors
              .map((message, hash) => (
                <p key={hash}>
                  <code>{message}</code>
                </p>
              ))
              .toList()}
          </pre>
        </div>
      )}
      <div className="max-h-[90vh] overflow-y-auto">
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={false}
          useDarkTheme={true}
          compareMethod={DiffMethod.LINES}
        />
      </div>
      <div className="my-3 text-center">
        <Link to={`/sort/choose`} className="text-sky-400">
          Back
        </Link>
        <span className="mx-6">
          <button
            className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
            onClick={() => beanCheck().catch(errorHandler)}
          >
            Check
          </button>
          {checkPassed && (
            <CheckCircleIcon className="w-5 h-5 inline ml-2 text-green-500" />
          )}
          {errors.size > 0 && (
            <ExclamationTriangleIcon className="w-5 h-5 inline ml-2  text-red-500" />
          )}
        </span>
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:opacity-25"
          onClick={() => writeChanges().catch(errorHandler)}
          disabled={checkPassed === undefined}
        >
          Write Changes
        </button>
      </div>
    </div>
  );
}
