import React from "react";
import { Link } from "react-router-dom";
import { BanknotesIcon } from "@heroicons/react/24/outline";

function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-2xl">
      <h2 className="text-5xl">Collecting Beans</h2>
      <BanknotesIcon className="w-[30vmin] h-[30vmin] animate-pulse" />
      <p>
        The following will update <code>data/*.beancount</code> when complete.
      </p>
      <Link to={`collect`} className="my-1">
        <button className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black">
          Collect New
        </button>
      </Link>
      <Link to={`sort`} className="my-1">
        <button className="border-solid border-2 rounded-full p-2 hover:bg-white hover:text-black">
          Sort Transactions
        </button>
      </Link>
    </div>
  );
}

export default App;
