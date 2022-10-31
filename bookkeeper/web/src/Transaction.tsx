import React from "react";
import dayjs from "dayjs";

import { IDirectiveForSort, IDirectiveMod, IPosting } from "./beanTypes";

export default function Transaction(props: {
  txn: IDirectiveForSort;
  // TODO: take in an "priorMods" to initialise the local "mods" state to
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
    </section>
  );
}

function Posting(props: { posting: IPosting }) {
  const { posting } = props;
  const isTodo = posting.account === "Equity:TODO";
  return (
    <pre className="max-w-[86ch] ml-[2ch]">
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
