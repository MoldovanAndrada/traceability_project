import type { JSONSchema7 } from 'json-schema';

import type { ComponentConfig } from 'src/codegen/ComponentConfig';

export interface SchemaFileProps {
  sortedKeys: string[];
  componentList: { [p: string]: string };
  configMap: { [key: string]: ComponentConfig };
}

export abstract class SchemaFile {

}
