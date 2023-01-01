import React from "react";
import { Link } from "react-router-dom";

export default function NavBar(props: {}) {
  return (
    <div className="mt-2 text-center">
      <Link to={`/`} className="text-sky-400">
        Home
      </Link>
    </div>
  );
}
