module.exports = {
  schedulerApi: {
    input: 'tmp/openapi.bundle.yaml',
    output: {
      target: 'src/api/endpoints.ts',
      schemas: 'src/api/models',
      client: 'react-query',
      httpClient: 'axios',
      clean: true
    },
    override: {
      mutator: {
        path: 'src/lib/httpClient.ts',
        name: 'client'
      }
    },
    hooks: {
      useQuery: true,
      useMutation: true,
      useInfiniteQuery: false
    }
  }
};
