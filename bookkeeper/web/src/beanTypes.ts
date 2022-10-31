export interface IDirectiveForSort {
  id: string;
  auto_category: string | null;
  entry: IDirective;
}
interface IDirective {
  date: string;
  filename: string;
  lineno: number;
  payee: string;
  narration: string;
  flag: string;
  tags: Array<string>;
  links: Array<string>;
  postings: Array<IPosting>;
}
interface IPosting {
  account: string;
  units: IAmount;
}
interface IAmount {
  number: string;
  currency: string;
}

export interface IDirectiveMod {
  // ID of the transaction from IDirectiveToSort
  id: string;
  // Only the _new_ postings that will replace the equity:todo posting.
  postings: Array<IPosting>;
}
