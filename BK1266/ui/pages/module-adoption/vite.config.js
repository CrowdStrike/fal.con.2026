import react from '@vitejs/plugin-react-swc'

const noAttr = () => ({
  name: 'no-attribute',
  transformIndexHtml(html) {
    return html.replace(/ crossorigin(?:="[^"]*")?/g, '')
  }
})

/** @type {import('vite').UserConfig} */
export default {
  plugins: [
    react(),
    noAttr()
  ],
  root: 'src',
  base: './'
};