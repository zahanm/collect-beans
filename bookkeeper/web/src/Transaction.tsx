import React, { useState } from "react";
import dayjs from "dayjs";
import { Set } from "immutable";
import { Combobox } from "@headlessui/react";

import { IDirectiveForSort, IDirectiveMod, IPosting } from "./beanTypes";

export default function Transaction(props: {
  txn: IDirectiveForSort;
  priorMod: IDirectiveMod | null;
  accounts: Set<string>;
  // TODO: take an "isEditing" to know whether this one is focussed
  onSave: (mod: IDirectiveMod) => void;
}) {
  const entry = props.txn.entry;
  const currency = Set(entry.postings.map((p) => p.units.currency)).first(
    "USD"
  );
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
      {props.priorMod ? (
        props.priorMod.postings.map((posting, idx) => (
          <Posting key={idx} posting={posting} />
        ))
      ) : (
        <EditPosting
          id={props.txn.id}
          autocat={props.txn.auto_category}
          currency={currency}
          accounts={props.accounts}
          onSave={props.onSave}
        />
      )}
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

function EditPosting(props: {
  id: string;
  autocat: string | null;
  currency: string;
  accounts: Set<string>;
  onSave: (mod: IDirectiveMod) => void;
}) {
  const [numPostings, setNumPostings] = useState(1);

  return (
    <form
      onSubmit={(ev) => {
        ev.preventDefault();
        console.log("submit", ev);
        const form = ev.target as HTMLFormElement;
        // Construct IDirectiveMod
        props.onSave({
          id: props.id,
          postings: arrayRange(numPostings).map((ii) => {
            const number = form[`${ii}-units-number`].value || null;
            return {
              account: form[`${ii}-account`].value,
              units: {
                number,
                currency:
                  number !== null ? form[`${ii}-units-currency`].value : "",
              },
            };
          }),
        });
      }}
    >
      {arrayRange(numPostings).map((ii) => (
        <div className="my-1" key={ii}>
          <pre className="w-[86ch] ml-[2ch] text-black inline-block">
            <AccountSelector
              name={`${ii}-account`}
              accounts={props.accounts}
              initValue={ii === 0 ? props.autocat : null}
            />
            <span className="float-right">
              <input
                type="text"
                className="max-w-[11ch] mr-[1ch] p-1 text-right"
                name={`${ii}-units-number`}
                placeholder="(optional)"
              />
              <input
                type="text"
                className="max-w-[4ch] p-1"
                name={`${ii}-units-currency`}
                required
                defaultValue={props.currency}
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

function AccountSelector(props: {
  accounts: Set<string>;
  name: string;
  initValue: string | null;
}) {
  const { accounts } = props;

  const [query, setQuery] = useState("");

  const filteredAccounts =
    query === ""
      ? accounts
      : accounts.filter((account) => {
          return account.toLowerCase().includes(query.toLowerCase());
        });

  return (
    <Combobox name={props.name} defaultValue={props.initValue}>
      <Combobox.Input
        className="min-w-[48ch] mr-2 p-1"
        required
        onChange={(event) => setQuery(event.target.value)}
      />
      <Combobox.Options>
        {filteredAccounts.map((account) => (
          <Combobox.Option key={account} value={account}>
            {account}
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
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
