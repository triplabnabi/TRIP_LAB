import { extendTheme } from '@chakra-ui/react';

const colors = {
  brand: {
    50: '#E0F7FA', // Light Cyan
    100: '#B2EBF2', // Pale Turquoise
    200: '#80DEEA', // Light Blue
    300: '#4DD0E1', // Sky Blue
    400: '#26C6DA', // Deep Sky Blue
    500: '#00BCD4', // Cyan
    600: '#00ACC1', // Dark Cyan
    700: '#0097A7', // Teal
    800: '#00838F', // Dark Teal
    900: '#006064', // Very Dark Teal
  },
  brightYellow: '#FFEB3B', // Bright Yellow
  lightPink: '#FFCDD2', // Light Pink
  vibrantGreen: '#8BC34A', // Vibrant Green
};

const theme = extendTheme({ colors });

export default theme;
