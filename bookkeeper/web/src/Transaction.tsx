import React, { useState } from "react";
import dayjs from "dayjs";

import { IDirectiveForSort, IDirectiveMod, IPosting } from "./beanTypes";

export default function Transaction(props: {
  txn: IDirectiveForSort;
  // TODO: take in an "priorMods" to initialise the local "mods" state to
  // TODO: take an "isEditing" to know whether this one is focussed
  onSort: (mods: Array<IDirectiveMod>) => void;
}) {
  const entry = props.txn.entry;
  return (
    <section className="my-2">
      <pre>
        <code className="text-lime-300">
          {dayjs(entry.date).format("YYYY-MM-DD")}
        </code>
        &nbsp;
        <code className="text-yellow-300">{entry.flag}</code>
        &nbsp;
        <code className="text-orange-300">&quot;{entry.payee}&quot;</code>
        &nbsp;
        <code className="text-orange-300">&quot;{entry.narration}&quot;</code>
      </pre>
      {entry.postings.map((posting, idx) => (
        <Posting key={idx} posting={posting} />
      ))}
      <EditPosting />
    </section>
  );
}

function Posting(props: { posting: IPosting }) {
  const { posting } = props;
  const isTodo = posting.account === "Equity:TODO";
  return (
    <pre className="w-[86ch] ml-[2ch]">
      <Account name={posting.account} isTodo={isTodo} />
      {!isTodo && (
        <span className="float-right">
          <code className="text-lime-300">{posting.units.number}</code>
          &nbsp;
          <code>{posting.units.currency}</code>
        </span>
      )}
    </pre>
  );
}

function Account(props: { name: string; isTodo: boolean }) {
  const [toplevel, ...rest] = props.name.split(":");
  return (
    <span className={props.isTodo ? "line-through" : ""}>
      <code className="text-cyan-500">{toplevel}</code>:
      <code className="text-sky-200">{rest.join(":")}</code>
    </span>
  );
}

function EditPosting(props: {}) {
  const [numPostings, setNumPostings] = useState(1);

  return (
    <form
      onSubmit={(ev) => {
        ev.preventDefault();
        console.log("submit", ev);
      }}
    >
      {arrayRange(numPostings).map((ii) => (
        <div className="my-1" key={ii}>
          <pre className="w-[86ch] ml-[2ch] text-black inline-block">
            <input
              type="text"
              className="min-w-[48ch] mr-2 p-1"
              name={String(ii) + "-account"}
              required
            />
            <span className="float-right">
              <input
                type="text"
                className="max-w-[11ch] mr-[1ch] p-1 text-right"
                name={String(ii) + "-units-number"}
                placeholder="(optional)"
              />
              <input
                type="text"
                className="max-w-[4ch] p-1"
                name={String(ii) + "-units-currency"}
                required
              />
            </span>
          </pre>
          {ii === 0 ? (
            <>
              <Save />
              <Add onClick={() => setNumPostings(numPostings + 1)} />
            </>
          ) : (
            <Minus onClick={() => setNumPostings(numPostings - 1)} />
          )}
        </div>
      ))}
    </form>
  );
}

function Save() {
  return (
    <button type="submit">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-5 h-5 inline ml-[1ch]"
      >
        <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
      </svg>
    </button>
  );
}

function Add(props: { onClick: () => void }) {
  return (
    <button onClick={props.onClick}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-5 h-5 inline ml-[1ch]"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-11.25a.75.75 0 00-1.5 0v2.5h-2.5a.75.75 0 000 1.5h2.5v2.5a.75.75 0 001.5 0v-2.5h2.5a.75.75 0 000-1.5h-2.5v-2.5z"
          clipRule="evenodd"
        />
      </svg>
    </button>
  );
}

function Minus(props: { onClick: () => void }) {
  return (
    <button onClick={props.onClick}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-5 h-5 inline ml-[1ch]"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM6.75 9.25a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z"
          clipRule="evenodd"
        />
      </svg>
    </button>
  );
}

function arrayRange(num: number): Array<number> {
  return [...Array(num).fill(0)].map((_, ii) => ii);
}
