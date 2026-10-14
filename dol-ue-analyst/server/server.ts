import { createApp, analytics, lakebase, server } from '@databricks/appkit';
import { setupInvestigationRoutes } from './routes/lakebase/investigation-routes';

createApp({
  plugins: [
    analytics(),
    lakebase(),
    server(),
  ],
  async onPluginsReady(appkit) {
    await setupInvestigationRoutes(appkit);
  },
}).catch(console.error);
