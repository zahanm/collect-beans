import React from "react";
import { Link } from "react-router-dom";

function SortChoose() {
  return (
    <div>
      <p>Actual choose flow</p>
      <Link to={`/sort/commit`} className="text-sky-400">
        Commit
      </Link>
    </div>
  );
}

export default SortChoose;
