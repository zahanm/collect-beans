import React, {
  ForwardedRef,
  forwardRef,
  Fragment,
  MutableRefObject,
  useState,
} from "react";
import dayjs from "dayjs";
import { Set } from "immutable";
import { Combobox, Transition } from "@headlessui/react";
import {
  PaperAirplaneIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  CheckIcon,
  ChevronUpDownIcon,
  ForwardIcon,
} from "@heroicons/react/20/solid";

import { IDirectiveForSort, IDirectiveMod, IPosting } from "./beanTypes";
import { arrayRange, invariant } from "./utilities";

type FwdInputsRef = ForwardedRef<Map<string, HTMLInputElement>>;
type OnSaveFn = (mod: IDirectiveMod) => void;
type OnSkipFn = (id: string) => void;

const JOURNAL_WIDTH = "w-10/12";

interface IProps {
  txn: IDirectiveForSort;
  accounts: Set<string>;
  editable: boolean;
  // Must provide either "priodMod" or "onSave". Mutually exclusive.
  priorMod?: IDirectiveMod;
  onSave?: OnSaveFn;
  onSkip?: OnSkipFn;
}
const Transaction = forwardRef((props: IProps, ref: FwdInputsRef) => {
  const entry = props.txn.entry;
  const currency = Set(entry.postings.map((p) => p.units.currency)).first(
    "USD"
  );
  invariant(
    !props.editable || !!ref,
    "Cannot leave out ref param if this is an editable entry"
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
        &nbsp;
        <code className="text-cyan-500">
          {entry.tags.map((t) => `#${t}`).join(" ")}
        </code>
      </pre>
      {entry.postings.map((posting, idx) => (
        <Posting key={idx} posting={posting} />
      ))}
      {props.editable ? (
        <EditPosting
          id={props.txn.id}
          ref={ref}
          autocat={props.txn.auto_category}
          currency={currency}
          accounts={props.accounts}
          onSave={props.onSave!}
          onSkip={props.onSkip!}
        />
      ) : (
        props.priorMod &&
        props.priorMod.postings.map((posting, idx) => (
          <Posting key={idx} posting={posting} />
        ))
      )}
    </section>
  );
});
export default Transaction;

function Posting(props: { posting: IPosting }) {
  const { posting } = props;
  const isTodo = posting.account === "Equity:TODO";
  return (
    <pre className={`${JOURNAL_WIDTH} ml-[2ch]`}>
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

interface IEditProps {
  id: string;
  autocat: string | null;
  currency: string;
  accounts: Set<string>;
  onSave: OnSaveFn;
  onSkip: OnSkipFn;
}
const EditPosting = forwardRef((props: IEditProps, ref: FwdInputsRef) => {
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
          <pre
            className={`${JOURNAL_WIDTH} ml-[2ch] text-black inline-flex justify-between`}
          >
            <AccountSelector
              id={props.id}
              name={`${ii}-account`}
              ref={ref}
              accounts={props.accounts}
              initValue={ii === 0 ? props.autocat : null}
            />
            <span className="text-right">
              <input
                type="text"
                className="w-[11ch] mr-[1ch] p-1 text-right rounded-lg"
                name={`${ii}-units-number`}
                placeholder="(optional)"
              />
              <input
                type="text"
                className="w-[4ch] p-1 rounded-lg"
                name={`${ii}-units-currency`}
                required
                defaultValue={props.currency}
              />
            </span>
          </pre>
          <span className="inline-block">
            {ii === 0 ? (
              <>
                {/* Don't want this selected through tabbing since I can hit enter anywhere else to submit */}
                <button type="submit" tabIndex={-1}>
                  <PaperAirplaneIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
                <button
                  onClick={() => setNumPostings(numPostings + 1)}
                  type="button"
                >
                  <PlusCircleIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
                <button onClick={() => props.onSkip(props.id)} type="button">
                  <ForwardIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
              </>
            ) : (
              <button
                onClick={() => setNumPostings(numPostings - 1)}
                type="button"
              >
                <MinusCircleIcon className="w-5 h-5 inline ml-[1ch]" />
              </button>
            )}
          </span>
        </div>
      ))}
    </form>
  );
});

interface IASProps {
  id: string;
  accounts: Set<string>;
  name: string;
  initValue: string | null;
}
const AccountSelector = forwardRef((props: IASProps, refs: FwdInputsRef) => {
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
      <div className="relative w-[48ch] inline-block">
        <div className="relative w-full cursor-default overflow-hidden rounded-lg text-left shadow-md">
          <Combobox.Input
            className="mr-2 p-1 w-full"
            required
            ref={(el: HTMLInputElement) => {
              const refsObj = refs as MutableRefObject<
                Map<string, HTMLInputElement>
              >;
              // Need a consistent indexing mechanism, so using the ID
              refsObj.current.set(props.id, el);
            }}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={(ev: any) => ev.target.select()}
          />
          <Combobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon className="h-5 w-5 text-gray-400" />
          </Combobox.Button>
        </div>
        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
          afterLeave={() => setQuery("")}
        >
          <Combobox.Options className="absolute mt-1 max-h-60 w-[48ch] z-10 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
            {filteredAccounts.size === 0 && query !== "" ? (
              <div className="relative cursor-default select-none py-2 px-4 text-gray-700">
                Nothing found.
              </div>
            ) : (
              filteredAccounts.map((account) => (
                <Combobox.Option
                  key={account}
                  value={account}
                  className={({ active }) =>
                    `relative cursor-default select-none py-2 pl-10 pr-4 ${
                      active ? "bg-teal-600 text-white" : "text-gray-900"
                    }`
                  }
                >
                  {({ selected, active }) => (
                    <>
                      <span
                        className={`block truncate ${
                          selected ? "font-medium" : "font-normal"
                        }`}
                      >
                        {account}
                      </span>
                      {selected ? (
                        <span
                          className={`absolute inset-y-0 left-0 flex items-center pl-3 ${
                            active ? "text-white" : "text-teal-600"
                          }`}
                        >
                          <CheckIcon className="h-5 w-5" />
                        </span>
                      ) : null}
                    </>
                  )}
                </Combobox.Option>
              ))
            )}
          </Combobox.Options>
        </Transition>
      </div>
    </Combobox>
  );
});
