import React, { useEffect } from "react";
import { Link } from "react-router-dom";

function SortOptions() {
  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch("http://localhost:5005/progress", {
        headers: {
          Accept: "application/json",
        },
      });
      const data = await resp.json();
      console.log(data);
    };

    fetchData().catch((err) => console.error(err));
  });

  return (
    <div>
      <h2>Start Sort</h2>
      <Link to={`/sort/choose`} className="text-sky-400">
        Next
      </Link>
    </div>
  );
}

export default SortOptions;
