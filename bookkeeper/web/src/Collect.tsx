import React, { useState } from "react";

import CollectOptions from "./CollectOptions";
import { CollectMode } from "./beanTypes";
import { invariant } from "./utilities";

export default function Collect() {
  const [collectMode, setCollectMode] = useState<CollectMode | null>(null);
  const [localSecrets, setLocalSecrets] = useState<string | null>(null);

  if (collectMode === null) {
    invariant(localSecrets === null);
  } else {
    invariant(localSecrets != null);
  }

  return collectMode != null ? <div>WIP</div> : <CollectOptions />;
}
