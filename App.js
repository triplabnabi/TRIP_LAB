import React from 'react';
import { ChakraProvider, Box, Text } from '@chakra-ui/react';
import theme from './theme';

function App() {
  return (
    <ChakraProvider theme={theme}>
      <Box
        bg="brand.500"
        w="100%"
        p={4}
        color="white"
        textAlign="center"
        fontSize="xl"
        fontWeight="bold"
      >
        Hello from a Bright Chakra UI Theme!
      </Box>
      <Box
        bg="lightPink"
        w="100%"
        p={4}
        mt={4}
        color="black"
        textAlign="center"
        fontSize="lg"
      >
        This is a light pink box.
      </Box>
      <Text mt={4} fontSize="2xl" color="vibrantGreen" textAlign="center">
        And this text is vibrant green!
      </Text>
    </ChakraProvider>
  );
}

export default App;
