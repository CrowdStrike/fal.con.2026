import React, { useContext } from "react";
import { Link as ReactRouterLink } from "react-router-dom";
import { FalconApiContext } from "../contexts/falcon-api-context";

function Link({
  children,
  useFalconNavigation = false,
  to,
  openInNewTab = false,
}) {
  const { falcon, navigation } = useContext(FalconApiContext);
  const absolutePath = falcon.bridge.targetOrigin.concat(to);

  const onClick = (e) => {
    e.preventDefault();
    navigation?.navigateTo({
      path: to,
      type: "falcon",
      target: openInNewTab ? "_blank" : "_self",
    });
  };
  if (useFalconNavigation) {
    return (
      <a onClick={onClick} href={absolutePath}>
        {children}
      </a>
    );
  }

  return <ReactRouterLink to={to}>{children}</ReactRouterLink>;
}

export { Link };
