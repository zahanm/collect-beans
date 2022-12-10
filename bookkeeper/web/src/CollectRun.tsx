import dayjs from "dayjs";
import React, { useState } from "react";

import { CollectMode } from "./beanTypes";

export interface SecretsSchema {
  importers: Array<ImporterSchema>;
}
interface ImporterSchema {
  name: string;
  access_token: string;
  institution_id: string;
  accounts: Array<AccountSchema>;
}
interface AccountSchema {
  name: string;
  plaid_id: string;
}

export default function CollectRun(props: {
  mode: CollectMode;
  secrets: SecretsSchema;
}) {
  const { mode, secrets } = props;

  const [startDate, setStartDate] = useState<string>(
    dayjs().subtract(30, "days").format("YYYY-MM-DD")
  );

  return (
    <div>
      <p className="p-4">
        We're running in <strong>{mode}</strong> mode
      </p>
      <div className="p-4">
        <h2 className="text-lg">Options</h2>
        <div className="grid grid-cols-2">
          <div>
            <p className="py-1">
              <label htmlFor="start_from" className="mr-1">
                Starting date
              </label>
              <input
                type="date"
                name="start_from"
                defaultValue={dayjs(startDate).format("YYYY-MM-DD")}
                required
                className="text-black px-2"
              />
            </p>
            <p className="py-1">
              <label htmlFor="skip_status" className="mr-1">
                Should skip institution status check
              </label>
              <select name="skip_status" className="text-black">
                <option value="yes">Yes</option>
                <option value="no" selected>
                  No
                </option>
              </select>
            </p>
          </div>
          <div className="flex items-center">
            <button className="bg-slate-700 px-1 border-solid border-2 rounded-lg hover:bg-white hover:text-black">
              Run all
            </button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2">
        <p className="p-4">
          We're running in <strong>{mode}</strong> mode
        </p>
        <p className="p-4">We have {secrets.importers.length} importers</p>
      </div>
    </div>
  );
}
