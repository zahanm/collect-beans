import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer";

import { errorHandler } from "./utilities";

const COMMIT_API = "http://localhost:5005/commit";

interface ICommitResponse {
  before: string;
  after: string;
}

function SortCommit() {
  const [before, setBefore] = useState<string>();
  const [after, setAfter] = useState<string>();

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch(COMMIT_API, {
        headers: {
          Accept: "application/json",
        },
      });
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
      headers: {
        Accept: "application/json",
      },
    });
    const data = (await resp.json()) as ICommitResponse;
    console.log("POST", data);
    setBefore(data.before);
    setAfter(data.after);
  };

  return (
    <div>
      <p>Commit the edits</p>
      <div className="max-h-[90vh] overflow-y-auto">
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={true}
          useDarkTheme={true}
          compareMethod={DiffMethod.LINES}
        />
      </div>
      <div className="mt-3 text-center">
        <Link to={`/`} className="text-sky-400 mr-6">
          Abort
        </Link>
        <button
          className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black"
          onClick={() => sendData().catch(errorHandler)}
        >
          Write Changes
        </button>
      </div>
    </div>
  );
}

export default SortCommit;
