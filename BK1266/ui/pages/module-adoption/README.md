# foundry-js-blueprint-react

React blueprint for Foundry UI application development.  

## Getting started

This project uses [pnpm](https://pnpm.io/) to manage dependencies.  Documentation to install `pnpm` is [here](https://pnpm.io/installation)

- `pnpm install`
- `pnpm watch`

`pnpm watch` will start [Vite](https://vite.dev/) in watch mode and your application's output will be under `/src/dist`.  The contents of `src/dist` is what will be rendered by Foundry.

## UI development

Included in this blueprint are some common css and React components you can use in your app. They're already styled to be consistent with the rest of Falcon Console and handle light and dark mode for you.

- [Shoelace](https://shoelace.style/frameworks/react) is already installed and we've also included [shoelace specific Falcon css](https://github.com/CrowdStrike/falcon-shoelace) to make the components provided by Shoelace look consistent with the rest of Falcon.

- [Tailwind Toucan Base](https://github.com/CrowdStrike/tailwind-toucan-base) is a [tailwindcss](https://tailwindcss.com/) theme that gives you utility classes you can use in html or React components. You have the full power of tailwind in this boilerplate.  The Falcon specific [colors](https://tailwind-toucan-base.pages.dev/#Colors) are a great place to start in Tailwind Toucan Base.

## Routing

This blueprint provides a [Link](/src/components/link.jsx) component to help with routing in your Extension or Page and within Falcon Console.

The `<Link>` component accepts these props:

- `to` - the path to navigate to
- `useFalconNavigation` - a boolean value indicating whether or not a link click will update the Falcon Console url.  Defaults to `false`
- `openInNewTab` - a boolean value indicating whether the link should open in a new tab.  Defaults to `false`

Setting `useFalconNavigation` to `true` will send the user to a new location within Falcon Console (this changes the Falcon Console url in the user's browser)

By default `useFalconNavigation` is set to `false` and React Router (included in this blueprint) will handle user navigation and UI changes within your app.

Usage of the `<Link>` component can be seen in the [home](/src/routes/home.jsx) and [navigation](/src/components/navigation.jsx) components.

```jsx
import { Link } from '../components/link';

// navigates to https://falcon.crowdstrike.com/activity
<Link useFalconNavigation={true} to="/activity">Activity Dashboard</Link>

// navigates to an /about route within your Extension or Page
<Link to="/about">About</Link>
```

## Building your app

Before deploying your Foundry app, you must do a final build of your UI extension so the app has access to the latest files in `/src/dist`.  Run the following build command when you're ready to deploy:

- `pnpm build`

## App manifest updates

### Add entries to your manifest's `ignored` field

When deploying your app, the `dist` directory is required and everything else can be ignored.  

Below are some starter regex patterns you can add to your app's `manifest.yml` file.

```yaml
ignored:
    - ui/(extensions|pages)/[^\/]*?/public
    - ui/(extensions|pages)/[^\/]*?/index.html
    - ui/(extensions|pages)/[^\/]*?/favicon.ico
    - ui/(extensions|pages)/.*?/node_modules
    - ui/(extensions|pages)/.*?/config
    - ui/(extensions|pages)/.*?/\.gitignore
    - ui/(extensions|pages)/.*?/package\.json
    - ui/(extensions|pages)/.*?/tsconfig\.json
    - ui/(extensions|pages)/.*?/tsconfig\..*\.json
    - ui/(extensions|pages)/.*?/.*?\.(md|log|lock|cjs)
```

Here's an example of how to set your manifest's [ignored](https://github.com/CrowdStrike/foundry-sample-mitre/blob/main/manifest.yml#L5-L30) field.

### Update your app's path and entrypoint

When using this React template, you must add `/dist` to the app path and entrypoint in the manifest file.

In the `manifest.yml` file, make the following changes (`{extensionName}` should be the name of your extension):

- Set `path` to this: `ui/extensions/{extensionName}/src/dist`
- Set `entrypoint` to this: `ui/extensions/{extensionName}/src/dist/index.html`

Here's an example of how to set your manifest's [path and entrypoint](https://github.com/CrowdStrike/foundry-sample-mitre/blob/main/manifest.yml#L39-L40) fields.