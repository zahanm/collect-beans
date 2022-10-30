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
      // NOTE that this is a plain text repsonse unlike the others
      const data = (await resp.json()) as ICommitResponse;
      console.log("GET", data);
      setBefore(data.before);
      setAfter(data.after);
    };

    fetchData().catch(errorHandler);
  }, []);

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
      <Link to={`/`} className="text-sky-400">
        Done
      </Link>
    </div>
  );
}

export default SortCommit;
