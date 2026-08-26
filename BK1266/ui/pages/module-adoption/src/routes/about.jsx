import React from "react";
import { SlDetails } from "@shoelace-style/shoelace/dist/react";

function About() {
  return (
    <div className={`mt-4 space-y-8`} style={{ maxWidth: "800px" }}>
      <SlDetails summary="Section One">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
        veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat.
      </SlDetails>
      <SlDetails summary="Section Two">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
        veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat.
      </SlDetails>
    </div>
  );
}

export { About };