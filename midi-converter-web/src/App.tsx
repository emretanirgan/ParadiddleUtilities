import { useEffect } from 'react';
import { ConverterPage } from './components/ConverterPage';
import { useMappingStore } from './stores/mapping-store';

function App() {
  const { useDefaultMapping, useDefaultDrumSet } = useMappingStore();

  // Load default assets on mount
  useEffect(() => {
    console.log('Loading default assets...');
    useDefaultMapping();
    useDefaultDrumSet();
  }, [useDefaultMapping, useDefaultDrumSet]);

  return <ConverterPage />;
}

export default App;
