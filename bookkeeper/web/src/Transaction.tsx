import React from "react";
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
  return (
    <div className="my-1">
      <form
        onSubmit={(ev) => {
          ev.preventDefault();
          console.log("submit", ev);
        }}
      >
        <pre className="w-[86ch] ml-[2ch] text-black inline-block">
          <input
            type="text"
            className="min-w-[48ch] mr-2 p-1"
            name="account"
            required
          />
          <span className="float-right">
            <input
              type="text"
              className="max-w-[11ch] mr-[1ch] p-1 text-right"
              name="units-number"
              placeholder="(optional)"
            />
            <input
              type="text"
              className="max-w-[4ch] p-1"
              name="units-currency"
              required
            />
          </span>
        </pre>
        <Save />
        {/* TODO: give an icon to add another Posting.
        But it won't have a Save button.
        Use the plus-circle icon. */}
      </form>
    </div>
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
