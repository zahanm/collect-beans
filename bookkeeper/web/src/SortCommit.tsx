import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer";
import { Map as ImmMap } from "immutable";

import { errorHandler } from "./utilities";

const COMMIT_API = "http://localhost:5005/sort/commit";
const CHECK_API = "http://localhost:5005/sort/check";

interface ICommitResponse {
  before: string;
  after: string;
}

interface ICheckResponse {
  check: boolean;
  errors: Record<string, string>;
}

export default function SortCommit() {
  const [before, setBefore] = useState<string>();
  const [after, setAfter] = useState<string>();
  const [checkPassed, setCheckPassed] = useState<boolean>(false);
  const [errors, setErrors] = useState<ImmMap<string, string>>(ImmMap());

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

  const sendData = async () => {
    const params = new URLSearchParams();
    // TODO: uncomment this in order to actually write to the file
    // params.append("write", "true");
    const url = new URL(COMMIT_API);
    url.search = params.toString();
    const resp = await fetch(url, {
      // TODO: uncomment this too
      // method: "POST",
    });
    const data = (await resp.json()) as ICommitResponse;
    console.log("POST", data);
    setBefore(data.before);
    setAfter(data.after);
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

  return (
    <div>
      <p>Commit the edits</p>
      <div className="max-h-[90vh] overflow-y-auto">
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={false}
          useDarkTheme={true}
          compareMethod={DiffMethod.LINES}
        />
      </div>
      {errors.size > 0 && (
        <div className="mx-6 text-red-500">
          <h2 className="text-xl my-2 font-semibold">
            New edits failed <code>bean-check</code>!
          </h2>
          <pre>
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
      <div className="mt-3 text-center">
        <Link to={`/sort/choose`} className="text-sky-400">
          Back
        </Link>
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black mx-6"
          onClick={() => beanCheck().catch(errorHandler)}
        >
          Check
        </button>
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:opacity-25"
          onClick={() => sendData().catch(errorHandler)}
          disabled={!checkPassed}
        >
          Write Changes
        </button>
      </div>
    </div>
  );
}
