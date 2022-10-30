import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function SortOptions() {
  const [journalFiles, setJournalFiles] = useState<Array<string>>([]);
  const [mainFile, setMainFile] = useState<string>();
  const [destFile, setDestFile] = useState<string>();

  useEffect(() => {
    const fetchData = async () => {
      const resp = await fetch("http://localhost:5005/progress", {
        headers: {
          Accept: "application/json",
        },
      });
      const data = await resp.json();
      console.log(data);
      setJournalFiles(data.journal_files);
    };

    fetchData().catch((err) => console.error(err));
  }, []);
  // The empty array of dependencies is important. It tells the
  // effect to only run once.

  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h2 className="text-xl">Start Sort</h2>
      <form
        onSubmit={(ev) => {
          ev.preventDefault();
          console.log("submitting form", ev);
        }}
      >
        <p className="py-1">
          <label htmlFor="main_file" className="mr-1">
            Main file:
          </label>
          <select
            name="main_file"
            value={mainFile}
            onChange={(ev) => setMainFile(ev.target.value)}
            required
            className="text-black"
          >
            {journalFiles.map((f) => (
              <option value={f} key={f}>
                {f}
              </option>
            ))}
          </select>
        </p>
        <p className="py-1">
          <label htmlFor="dest_file" className="mr-1">
            Destination file:
          </label>
          <select
            name="dest_file"
            value={destFile}
            onChange={(ev) => setDestFile(ev.target.value)}
            required
            className="text-black"
          >
            {journalFiles.map((f) => (
              <option value={f} key={f}>
                {f}
              </option>
            ))}
          </select>
        </p>
        <p className="py-1 text-center">
          <button type="submit">Save</button>
        </p>
      </form>
      <div>
        <Link to={`/`} className="text-sky-400 mr-10">
          Cancel
        </Link>
        <Link to={`/sort/choose`} className="text-sky-400">
          Start
        </Link>
      </div>
    </div>
  );
}

export default SortOptions;
