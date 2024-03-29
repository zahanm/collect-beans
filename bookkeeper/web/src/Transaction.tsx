import React, {
  FormEvent,
  ForwardedRef,
  forwardRef,
  Fragment,
  MutableRefObject,
  useState,
} from "react";
import dayjs from "dayjs";
import { List, Set } from "immutable";
import { Combobox, Transition } from "@headlessui/react";
import {
  PaperAirplaneIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  CheckIcon,
  ChevronUpDownIcon,
  ForwardIcon,
  TrashIcon,
  LinkIcon,
} from "@heroicons/react/20/solid";

import { IDirectiveForSort, IDirectiveMod, IPosting } from "./beanTypes";
import { absDiff, arrayRange, invariant } from "./utilities";

type FwdInputsRef = ForwardedRef<Map<string, HTMLInputElement>>;
type OnSaveFn = (mod: IDirectiveMod) => void;
type OnRevertFn = (txnID: string) => void;
type OnLinkFn = (txnID: string) => void;

const JOURNAL_WIDTH = "w-10/12";
const TAG_SKIP_SORT = "skip-sort";

interface IProps {
  txn: IDirectiveForSort;
  accounts?: Set<string>;
  postingsEdit: boolean;
  // Must provide either "priodMod" or "onSave". Mutually exclusive.
  priorMod?: IDirectiveMod;
  onSave?: OnSaveFn;
  onRevert?: OnRevertFn;
  onLink?: OnLinkFn;
}
const Transaction = forwardRef((props: IProps, ref: FwdInputsRef) => {
  invariant(
    !props.postingsEdit || ref,
    "Cannot leave out ref param if this is an editable entry"
  );
  invariant(
    !props.postingsEdit || props.accounts,
    "Must provide accounts if this is an editable entry"
  );

  const entry = props.txn.entry;
  const currency = Set(entry.postings.map((p) => p.units.currency)).first(
    "USD"
  );
  const amountToSort = entry.postings.find((p) => p.account === "Equity:TODO")!
    .units.number!;
  const [numNewPosts, setNumNewPosts] = useState(1);
  const [firstLineEdit, setFirstLineEdit] = useState(false);

  const saveChanges = (ev: FormEvent<HTMLFormElement>) => {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    if (props.postingsEdit) {
      const sum = arrayRange(numNewPosts)
        .map((ii) => {
          return parseFloat(form[`${ii}-units-number`].value);
        })
        .reduce((acc, v) => acc + v, 0);
      const reportInput = form[`${numNewPosts - 1}-units-number`];
      if (absDiff(sum, parseFloat(amountToSort)) > 0.005) {
        reportInput.setCustomValidity("The transaction does not balance");
        reportInput.reportValidity();
        return;
      }
    }
    const mod: IDirectiveMod = props.priorMod || {
      id: props.txn.id,
      type: "replace",
    };
    if (props.postingsEdit) {
      mod["postings"] = arrayRange(numNewPosts).map((ii) => {
        return {
          account: form[`${ii}-account`].value,
          units: {
            number: form[`${ii}-units-number`].value,
            currency: form[`${ii}-units-currency`].value,
          },
        };
      });
    }
    if (firstLineEdit) {
      if (form["payee"].value) {
        mod["payee"] = form["payee"].value;
      }
      if (form["narration"].value) {
        mod["narration"] = form["narration"].value;
      }
    }
    setFirstLineEdit(false);
    props.onSave!(mod);
    console.log("submit", ev, mod);
  };

  return (
    <section className="my-2">
      <form onSubmit={saveChanges}>
        <FirstLine
          txn={props.txn}
          editable={firstLineEdit}
          saved={!props.postingsEdit}
          priorMod={props.priorMod}
          onRevert={props.onRevert}
          onLink={props.onLink}
          makeEditable={() => setFirstLineEdit(true)}
        />
        {entry.postings.map((posting, idx) => (
          <Posting key={idx} posting={posting} priorMod={props.priorMod} />
        ))}
        {props.postingsEdit ? (
          <EditPosting
            id={props.txn.id}
            ref={ref}
            autocat={props.txn.auto_category}
            amountToSort={amountToSort}
            currency={currency}
            accounts={props.accounts!}
            onSave={props.onSave!}
            numNewPosts={numNewPosts}
            onChangeNumNewPosts={setNumNewPosts}
          />
        ) : (
          props.priorMod &&
          props.priorMod.postings &&
          props.priorMod.postings.map((posting, idx) => (
            <Posting key={idx} posting={posting} priorMod={props.priorMod} />
          ))
        )}
      </form>
    </section>
  );
});
export default Transaction;

function FirstLine(props: {
  txn: IDirectiveForSort;
  editable: boolean;
  saved: boolean;
  priorMod?: IDirectiveMod;
  onRevert?: OnRevertFn;
  onLink?: OnLinkFn;
  makeEditable: () => void;
}) {
  const { entry } = props.txn;
  invariant(
    !props.saved || props.onRevert,
    "Must provide onRevert if saved is true"
  );
  const deleted = !!(props.priorMod && props.priorMod.type === "delete");
  const tags = Set(entry.tags).concat(
    props.priorMod && props.priorMod.type === "skip" ? [TAG_SKIP_SORT] : []
  );

  return (
    <div>
      <pre
        className={`${JOURNAL_WIDTH} inline-block ${
          deleted ? "line-through" : ""
        }`}
      >
        <code className="text-lime-300">
          {dayjs(entry.date).format("YYYY-MM-DD")}
        </code>
        &nbsp;
        <code className="text-yellow-300">{entry.flag}</code>
        &nbsp;
        {props.editable ? (
          <>
            <input
              type="text"
              name="payee"
              className="text-orange-500 w-[28ch] p-1 rounded-lg"
              defaultValue={
                (props.priorMod && props.priorMod.payee) || entry.payee
              }
              placeholder="Payee"
              required
            />
            <input type="submit" hidden />
          </>
        ) : (
          <code className="text-orange-300" onClick={props.makeEditable}>
            &quot;
            {(props.priorMod && props.priorMod.payee) || entry.payee}
            &quot;
          </code>
        )}
        &nbsp;
        {props.editable ? (
          <input
            type="text"
            name="narration"
            className="text-orange-500 w-[42ch] p-1 rounded-lg"
            defaultValue={
              (props.priorMod && props.priorMod.narration) || entry.narration
            }
            placeholder="Narration"
          />
        ) : (
          <code className="text-orange-300" onClick={props.makeEditable}>
            &quot;
            {(props.priorMod && props.priorMod.narration) || entry.narration}
            &quot;
          </code>
        )}
        &nbsp;
        <code className="text-cyan-500">
          {tags.map((t) => `#${t}`).join(" ")}
        </code>
      </pre>
      {props.saved && (
        <span className="inline-block ml-[2ch]">
          <button type="button" onClick={() => props.onRevert!(props.txn.id)}>
            <MinusCircleIcon className="w-5 h-5 inline ml-[1ch]" />
          </button>
          {props.onLink && (
            <button type="button" onClick={() => props.onLink!(props.txn.id)}>
              <LinkIcon className="w-5 h-5 inline ml-[1ch]" />
            </button>
          )}
        </span>
      )}
    </div>
  );
}

function Posting(props: { posting: IPosting; priorMod?: IDirectiveMod }) {
  const { posting } = props;
  const deleted = !!(props.priorMod && props.priorMod.type === "delete");
  const isTodo = posting.account === "Equity:TODO";
  const isDebit = Number(posting.units.number) < 0;
  return (
    <pre className={`${JOURNAL_WIDTH} ml-[2ch]`}>
      <Account name={posting.account} deleted={deleted || isTodo} />
      {!isTodo && (
        <span className={`float-right ${deleted ? "line-through" : ""}`}>
          <code className={isDebit ? "text-red-300" : "text-lime-300"}>
            {posting.units.number}
          </code>
          &nbsp;
          <code>{posting.units.currency}</code>
        </span>
      )}
    </pre>
  );
}

function Account(props: { name: string; deleted: boolean }) {
  const [toplevel, ...rest] = props.name.split(":");
  return (
    <span className={props.deleted ? "line-through" : ""}>
      <code className="text-cyan-500">{toplevel}</code>:
      <code className="text-sky-200">{rest.join(":")}</code>
    </span>
  );
}

interface IEditProps {
  id: string;
  autocat: string | null;
  amountToSort: string;
  currency: string;
  accounts: Set<string>;
  onSave: OnSaveFn;
  numNewPosts: number;
  onChangeNumNewPosts: (num: number) => void;
}
const EditPosting = forwardRef((props: IEditProps, ref: FwdInputsRef) => {
  const { amountToSort, numNewPosts, onChangeNumNewPosts } = props;

  const [amounts, setAmounts] = useState<List<string>>(() => {
    const init = [...Array(numNewPosts).fill("0.00")];
    init[0] = amountToSort;
    return List(init);
  });

  invariant(amounts.size === numNewPosts);

  return (
    <>
      {arrayRange(numNewPosts).map((ii) => (
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
                required
                value={amounts.get(ii)}
                onChange={(ev) => {
                  setAmounts(amounts.set(ii, ev.target.value));
                  ev.target.setCustomValidity("");
                }}
                placeholder="0.00"
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
                  onClick={() => {
                    const sum = amounts.reduce(
                      (ac, v) => ac + parseFloat(v),
                      0
                    );
                    const rem = parseFloat(amountToSort) - sum;
                    setAmounts(amounts.push(rem.toFixed(2)));
                    onChangeNumNewPosts(numNewPosts + 1);
                  }}
                  type="button"
                >
                  <PlusCircleIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    props.onSave({
                      id: props.id,
                      type: "skip",
                    });
                  }}
                >
                  <ForwardIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    props.onSave({
                      id: props.id,
                      type: "delete",
                    });
                  }}
                >
                  <TrashIcon className="w-5 h-5 inline ml-[1ch]" />
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  setAmounts(amounts.pop());
                  onChangeNumNewPosts(numNewPosts - 1);
                }}
                type="button"
              >
                <MinusCircleIcon className="w-5 h-5 inline ml-[1ch]" />
              </button>
            )}
          </span>
        </div>
      ))}
    </>
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
              // If nothing is found, allow a custom entry.
              <Combobox.Option
                key={query}
                value={query}
                className={({ active }) =>
                  `relative cursor-default select-none py-2 pl-10 pr-4 ${
                    active ? "bg-teal-600 text-white" : "text-gray-900"
                  }`
                }
              >
                <span className="block truncate font-normal">{query}</span>
              </Combobox.Option>
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
