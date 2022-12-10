import React, { useState } from "react";

import CollectOptions from "./CollectOptions";
import CollectRun, { SecretsSchema } from "./CollectRun";
import { CollectMode } from "./beanTypes";
import { invariant } from "./utilities";

export default function Collect() {
  const [collectMode, setCollectMode] = useState<CollectMode | null>(null);
  const [localSecrets, setLocalSecrets] = useState<SecretsSchema | null>(null);

  if (collectMode === null) {
    invariant(localSecrets === null);
  } else {
    invariant(localSecrets != null);
  }

  return collectMode != null && localSecrets != null ? (
    <CollectRun mode={collectMode} secrets={localSecrets} />
  ) : (
    <CollectOptions
      onSecretsSubmit={(mode, statestring) => {
        setCollectMode(mode);
        const secrets = JSON.parse(statestring) as SecretsSchema;
        setLocalSecrets(secrets);
      }}
    />
  );
}
