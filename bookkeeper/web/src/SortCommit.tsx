import React from "react";
import { Link } from "react-router-dom";

function SortCommit() {
  return (
    <div>
      <p>Commit the edits</p>
      <Link to={`/`}>Done</Link>
    </div>
  );
}

export default SortCommit;
