rm tf.min.js
rm tf-backend-wasm.js
wget https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@2.1.0/dist/tf.min.js
wget https://cdn.jsdelivr.net/npm/@tensorflow/tfjs-backend-wasm@2.1.0/dist/tf-backend-wasm.js

# For .wasm file, sudo npm install -g @tensorflow/tfjs-backend-wasm -> Navigate to dist/tfjs-backend-wasm.wasm
#	See https://github.com/tensorflow/tfjs/tree/master/tfjs-backend-wasm