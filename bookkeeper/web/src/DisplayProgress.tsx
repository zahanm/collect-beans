import React from "react";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/20/solid";

export type TProgress = "idle" | "in-process" | "success" | "error";

export default function DisplayProgress(props: {
  progress: TProgress;
  className: string;
}) {
  const { progress, ...rest } = props;
  switch (progress) {
    case "idle":
      return <></>;

    case "in-process":
      return (
        <span {...rest}>
          <ArrowPathIcon className="w-5 h-5 inline animate-spin" />
        </span>
      );

    case "success":
      return (
        <span {...rest}>
          <CheckCircleIcon className="w-5 h-5 inline" />
        </span>
      );

    case "error":
      return (
        <span {...rest}>
          <ExclamationTriangleIcon className="w-5 h-5 inline" />
        </span>
      );
  }
}
