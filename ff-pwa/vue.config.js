const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
    configureWebpack: (config) => {
        // For some reason push causes it to fail. Something to do with the last
        //  entry in the rules being slightly different (has a pre field?). I am
        //  not experienced enough with Vue / Webpack to read any more into this.
        config.module.rules.unshift({
            test: /\.worker\.js$/i,
            use: [
                {
                    loader: 'comlink-loader',
                    options: {
                        singleton: true
                    }
                }
            ]
        });

        config.plugins.push(
            new CopyPlugin({
                patterns: [
                    {from: 'src/folkfriend/ff-wasm.wasm', to: 'js/ff-wasm.wasm'},
                    {from: 'src/folkfriend/shaders/fragment.glsl', to: 'shaders/fragment.glsl'},
                    {from: 'src/folkfriend/shaders/vertex.glsl', to: 'shaders/vertex.glsl'}
                ],
            })
        );

        // https://github.com/tensorflow/tfjs/tree/master/tfjs-backend-wasm/starter/webpack
        // config.module.rules.unshift({
        //         test: /\.wasm$/i,
        //         type: 'javascript/auto',
        //         loader: 'file-loader',
        //         options: {
        //             publicPath: "dist/"
        //         }
        //     },
        // );

        // config.node = {
        //     fs: "empty"
        // };
    }
};
