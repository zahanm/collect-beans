import React from "react";
import { Link } from "react-router-dom";

function SortOptions() {
  return (
    <div>
      <p>Set sort options</p>
      <Link to={`/sort/choose`} className="text-sky-400">
        Next
      </Link>
    </div>
  );
}

export default SortOptions;
